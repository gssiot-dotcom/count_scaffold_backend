#serializer.py
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import (
    Company, Site, User, SiteAssignment,
    Material, Rental, RentalDetail,
    RentalMovement, RentalMovementDetail, AIRecognition, ReturnRequestDetail, ReturnRequest  # Report 삭제, Movement 추가
)

# =========================
# 회사 & 현장
# =========================
class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = '__all__'
        extra_kwargs = {
            'company': {'required': False}
        }

# =========================
# 유저 (조회용)
# =========================
class UserSerializer(serializers.ModelSerializer):
    # 모델의 get_role_display 기능을 통해 '현장 총책임자' 같은 한글명을 가져옵니다.
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    # 관계형 필드에서 ID 대신 이름을 바로 보여주도록 설정합니다.
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    site_name = serializers.CharField(source="site.site_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "company",
            "company_name",  # 프론트 화면용
            "site",
            "site_name",  # 프론트 화면용
            "name",
            "phone",
            "email",
            "role",  # 서버 로직/권한 체크용 ('siteManager' 등)
            "role_display",  # 프론트 화면 표시용 ('현장 총책임자' 등)
            "is_approved",
            "created_at",
        ]


# =========================
# 유저 생성 (회원가입)
# =========================
class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['company', 'site', 'name', 'phone', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
            'site': {'required': False, 'allow_null': True}
        }

    # 🔥 회사-현장 검증 (중요)
    def validate(self, data):
        company = data.get("company")
        site = data.get("site")

        if site and site.company != company:
            raise serializers.ValidationError("현장은 해당 회사 소속이어야 합니다.")

        return data

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])
        validated_data.setdefault("role", "siteWorker")  # 기본값
        validated_data["is_approved"] = False            # 승인 대기
        return super().create(validated_data)


# =========================
# 자재
# =========================
class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = '__all__'

        read_only_fields = ['company']


# =========================
# 현장 권한 할당
# =========================
class SiteAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteAssignment
        fields = '__all__'

# =========================
# 1. Rental (계약 - 프론트엔드 표시용 필드 추가)
# =========================
class RentalSerializer(serializers.ModelSerializer):
    requester_company_name = serializers.CharField(source="requester_company.company_name", read_only=True)
    provider_company_name = serializers.CharField(source="provider_company.company_name", read_only=True)
    site_name = serializers.CharField(source="site.site_name", read_only=True)

    class Meta:
        model = Rental
        fields = '__all__'
        read_only_fields = ['created_at']


# =========================
# 2. RentalDetail (계약 자재 목록 및 누적 집계 데이터 포함)
# =========================
class RentalDetailSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source="material.material_name", read_only=True)
    material_spec = serializers.CharField(source="material.spec", read_only=True)

    # 🔥 models.py에서 작성한 @property(집계) 함수들을 API로 내보내기 위해 필드 선언
    total_out_qty = serializers.ReadOnlyField()
    total_site_received_qty = serializers.ReadOnlyField()
    total_return_qty = serializers.ReadOnlyField()
    total_final_in_qty = serializers.ReadOnlyField()
    total_loss_qty = serializers.ReadOnlyField()
    current_site_qty = serializers.ReadOnlyField()

    class Meta:
        model = RentalDetail
        fields = '__all__'


# =========================
# 3. RentalMovementDetail (회차별 자재 수량)
# =========================
class RentalMovementDetailSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source="material.material_name", read_only=True)
    material_spec = serializers.CharField(source="material.spec", read_only=True)

    class Meta:
        model = RentalMovementDetail
        fields = '__all__'


# =========================
# 4. RentalMovement (입출고 회차 - 프론트엔드 맞춤형)
# =========================
class RentalMovementSerializer(serializers.ModelSerializer):
    # 1. 위에서 만든 진짜 DetailSerializer를 여기서 가져다 씁니다.
    movement_details = RentalMovementDetailSerializer(many=True, read_only=True)

    # 2. 부모 테이블(Rental)을 타고 올라가서 현장과 회사 이름들을 가져옵니다.
    site_name = serializers.CharField(source="rental.site.site_name", read_only=True)
    requester_company_name = serializers.CharField(source="rental.requester_company.company_name", read_only=True)
    provider_company_name = serializers.CharField(source="rental.provider_company.company_name", read_only=True)

    class Meta:
        model = RentalMovement
        fields = '__all__'
        read_only_fields = ['created_at']


# =========================
# 5. AIRecognition
# =========================
class AIRecognitionSerializer(serializers.ModelSerializer):
    # 쓰기/읽기 모두 가능, 빈칸 허용
    image = serializers.ImageField(required=False, allow_null=True)
    movement_detail = serializers.PrimaryKeyRelatedField(
        queryset=RentalMovementDetail.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = AIRecognition
        fields = '__all__'

        extra_kwargs = {
            'movement_detail': {'required': False, 'allow_null': True}
        }


# =========================================================
# 반납 요청 상세 (ReturnRequestDetail)
# =========================================================
class ReturnRequestDetailSerializer(serializers.ModelSerializer):
    # 프론트엔드가 자재 이름/규격을 바로 볼 수 있게 추가
    material_name = serializers.CharField(source="rental_detail.material.material_name", read_only=True)
    material_spec = serializers.CharField(source="rental_detail.material.spec", read_only=True)

    class Meta:
        model = ReturnRequestDetail
        fields = '__all__'


# =========================================================
# 반납 요청 부모 (ReturnRequest)
# =========================================================
class ReturnRequestSerializer(serializers.ModelSerializer):
    details = ReturnRequestDetailSerializer(many=True, read_only=True)

    # 프론트엔드 화면용 추가 정보
    site_name = serializers.CharField(source="rental.site.site_name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)  # 작성자 이름도 보내주면 좋습니다

    class Meta:
        model = ReturnRequest
        fields = '__all__'