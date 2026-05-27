#models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

# =========================
# 회사
# =========================
class Company(models.Model):
    company_name = models.CharField(max_length=100)
    ceo_name = models.CharField(max_length=50)
    company_contact = models.CharField(max_length=20)
    company_address = models.CharField(max_length=255)

    # 대여업체 여부 (에이티엔, 의조 등)
    is_provider = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.company_name


# =========================
# 현장
# =========================
class Site(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='sites'
    )
    site_name = models.CharField(max_length=100)
    site_address = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.site_name


# =========================
# 회원
# =========================
class User(models.Model):
    ROLE_CHOICES = (
        ('siteWorker', '현장 직원'),
        ('siteManager', '현장 총책임자'),
        ('officeWorker', '사무실 직원'),
        ('officeManager', '사무실 총책임자'),
        ('superAdmin', '최고 관리자'),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='users'
    )

    # ⭐ 현장 소속 (현장 직원/책임자용)
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )

    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='siteWorker'
    )

    # ⭐ 사무실 총책임자 승인 여부
    is_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"[{self.company.company_name}] {self.name} ({self.get_role_display()})"


# =========================
# 권한 할당 (사무실 직원 ↔ 현장)
# =========================
class SiteAssignment(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_sites'
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='assigned_users'
    )

    # 누가 권한 줬는지 (officeManager)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='managed_assignments'
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'site')  # 중복 할당 방지


# =========================
# 자재
# =========================
class Material(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='materials'
    )

    material_name = models.CharField(max_length=100)
    spec = models.CharField(max_length=50)

    price = models.DecimalField(max_digits=10, decimal_places=0)

    # 재고 관리
    total_qty = models.IntegerField(default=0)
    loss_qty = models.IntegerField(default=0)
    repaired_qty = models.IntegerField(default=0)
    disposed_qty = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.material_name} - {self.company.company_name}"


# =========================================================
# 1. Rental (전체 거래 계약 - 신규/수정)
# =========================================================
class Rental(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "작성중"),  # 견적서 업로드 후 확정 전
        ("REQUESTED", "승인대기"),
        ("APPROVED", "대여승인"),
        ("ACTIVE", "진행중"),
        ("COMPLETED", "거래완료"),  # 모든 자재 반납 완료
        ("CLOSED", "계약종료"),
        ("CANCELLED", "계약취소"),
    ]

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='rentals')
    provider_company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='provided_rentals')
    requester_company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='requested_rentals')
    requester_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_rentals')

    quotation_file = models.FileField(upload_to='quotations/%Y/%m/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="REQUESTED")

    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="approved_rentals")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rental #{self.id} - {self.status}"


# =========================================================
# 2. RentalDetail (계약 자재 목록 및 누적 집계 - 신규/수정)
# =========================================================
class RentalDetail(models.Model):
    rental = models.ForeignKey(Rental, on_delete=models.CASCADE, related_name='details')
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    planned_qty = models.IntegerField(default=0)  # 견적서 상 최초 계약 수량

    # [집계] 하위 MovementDetail들을 합산
    @property
    def total_out_qty(self):
        return sum(md.office_out_qty for md in
                   self.movement_details.filter(movement__movement_type="OUT", movement__status="OUT_COMPLETED"))

    @property
    def total_site_received_qty(self):
        return sum(md.site_receive_qty for md in
                   self.movement_details.filter(movement__movement_type="OUT", movement__status="OUT_COMPLETED"))

    @property
    def total_return_qty(self):
        return sum(md.return_qty for md in
                   self.movement_details.filter(movement__movement_type="RETURN", movement__status="RETURN_COMPLETED"))

    @property
    def total_final_in_qty(self):
        return sum(md.final_in_qty for md in
                   self.movement_details.filter(movement__movement_type="RETURN", movement__status="RETURN_COMPLETED"))

    @property
    def total_loss_qty(self):
        return sum(md.loss_qty for md in self.movement_details.filter(movement__movement_type="RETURN"))

    @property
    def current_site_qty(self):
        # 현재 현장 잔여 수량 = 누적 현장 수령 - 누적 반납 - 누적 LOSS/폐기
        total_discarded = sum(md.discarded_qty for md in self.movement_details.filter(movement__movement_type="RETURN"))
        return self.total_site_received_qty - self.total_return_qty - self.total_loss_qty - total_discarded

    @property
    def is_fully_returned(self):
        # 현장 잔여 수량이 0 이하면 완전 반납
        return self.current_site_qty <= 0

# =========================================================
# 3. RentalMovement (실제 출고/반납 회차 - 신규)
# =========================================================
class RentalMovement(models.Model):
    TYPE_OUT = "OUT"
    TYPE_RETURN = "RETURN"

    STATUS_CHOICES = [
        ("OUT_CREATED", "출고 생성"),
        ("OUT_OFFICE_CHECKED", "사무실 확인완료"),
        ("OUT_OFFICE_SIGNED", "사무실 서명완료"),
        ("OUT_IN_TRANSIT", "현장 이동중"),
        ("OUT_SITE_RECEIVED", "현장 수령확인"),
        ("OUT_SITE_SIGNED", "현장 서명완료"),
        ("OUT_COMPLETED", "출고 완료"),

        ("RETURN_CREATED", "반납 생성"),
        ("RETURN_SITE_CHECKED", "현장 확인완료"),
        ("RETURN_SITE_SIGNED", "현장 서명완료"),
        ("RETURN_IN_TRANSIT", "공장 이동중"),
        ("RETURN_FACTORY_CHECKED", "공장 검수완료"),
        ("RETURN_OFFICE_SIGNED", "사무실 서명완료"),
        ("RETURN_COMPLETED", "반납 완료"),
    ]

    rental = models.ForeignKey(Rental, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=10, choices=[(TYPE_OUT, "출고"), (TYPE_RETURN, "반납")])
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_movements")
    created_at = models.DateTimeField(auto_now_add=True)

    # --- 서명 및 사진 정보 (기존 Report 모델 대체) ---
    office_out_photo = models.ImageField(upload_to="movements/out/", null=True, blank=True)
    office_out_signature = models.ImageField(upload_to="signatures/out/", null=True, blank=True)
    office_out_signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                             related_name="signed_out_movements")

    site_receive_photo = models.ImageField(upload_to="movements/receive/", null=True, blank=True)
    site_receive_signature = models.ImageField(upload_to="signatures/receive/", null=True, blank=True)
    site_receive_signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                               related_name="signed_receive_movements")

    site_return_photo = models.ImageField(upload_to="movements/return/", null=True, blank=True)
    site_return_signature = models.ImageField(upload_to="signatures/return/", null=True, blank=True)
    site_return_signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                              related_name="signed_site_return_movements")

    office_in_photo = models.ImageField(upload_to="movements/in/", null=True, blank=True)
    office_in_signature = models.ImageField(upload_to="signatures/in/", null=True, blank=True)
    office_in_signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                            related_name="signed_in_movements")


# =========================================================
# 4. RentalMovementDetail (회차별 자재 상세 수량 - 신규)
# =========================================================
class RentalMovementDetail(models.Model):
    movement = models.ForeignKey(RentalMovement, on_delete=models.CASCADE, related_name="movement_details")
    rental_detail = models.ForeignKey(RentalDetail, on_delete=models.CASCADE, related_name="movement_details")
    material = models.ForeignKey(Material, on_delete=models.CASCADE)

    # OUT 수량
    request_qty = models.IntegerField(default=0)  # 현장에서 요청한 출고 수량
    office_out_qty = models.IntegerField(default=0)  # 사무실 출고 확정 수량
    site_receive_qty = models.IntegerField(default=0)  # 현장 수령 수량

    # RETURN 수량
    site_request_return_qty = models.IntegerField(default=0)  # 현장 반납 요청 수량
    return_qty = models.IntegerField(default=0)  # 현장 반납 확정 수량
    final_in_qty = models.IntegerField(default=0)  # 공장 최종 입고 수량

    # 예외 수량 (검수 시 확정)
    loss_qty = models.IntegerField(default=0)
    broken_qty = models.IntegerField(default=0)
    repaired_qty = models.IntegerField(default=0)
    discarded_qty = models.IntegerField(default=0)


# =========================================================
# 5. AIRecognition (타겟 변경: RentalDetail -> MovementDetail)
# =========================================================
class AIRecognition(models.Model):
    movement_detail = models.ForeignKey(
        RentalMovementDetail,
        on_delete=models.SET_NULL,  # CASCADE 대신 SET_NULL로 변경 (장부 삭제돼도 사진은 남도록)
        null=True,                  # DB에 빈칸(NULL) 저장 허용
        blank=True,                 # 폼(API)에서 빈칸 전송 허용
        related_name='ai_results'
    )

    return_request_detail = models.ForeignKey(
        'ReturnRequestDetail', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ai_results'
    )

    detected_qty = models.IntegerField()
    corrected_qty = models.IntegerField(null=True, blank=True)
    image = models.ImageField(upload_to='ai/')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"AI Qty: {self.detected_qty}"

# =========================================================
# 6. ReturnRequest (반납 신청 - 현장 → 사무실)
# =========================================================
class ReturnRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "대기중"),
        ("ACCEPTED", "처리완료")
    ]
    rental = models.ForeignKey(Rental, on_delete=models.CASCADE, related_name="return_requests")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    photo = models.ImageField(upload_to="return_requests/photos/", null=True, blank=True)
    signature = models.ImageField(upload_to="return_requests/signatures/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ReturnRequestDetail(models.Model):
    return_request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name="details")
    rental_detail = models.ForeignKey(RentalDetail, on_delete=models.CASCADE)
    request_qty = models.IntegerField(default=0)