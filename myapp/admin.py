from django.contrib import admin
from .models import (
    Company, Site, User, SiteAssignment,
    Material, Rental, RentalDetail,
    RentalMovement, RentalMovementDetail, AIRecognition
)

# ---------------------------------------------------------
# 인라인 설정: 부모 데이터 안에서 자식 데이터를 바로 수정/조회
# ---------------------------------------------------------

class RentalDetailInline(admin.TabularInline):
    model = RentalDetail
    extra = 0

class RentalMovementInline(admin.TabularInline):
    model = RentalMovement
    extra = 0

class MovementDetailInline(admin.TabularInline):
    model = RentalMovementDetail
    extra = 0

# ---------------------------------------------------------
# 관리자 클래스 설정
# ---------------------------------------------------------

@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ['id', 'requester_company', 'site', 'status', 'created_at']
    list_filter = ['status', 'requester_company']
    inlines = [RentalDetailInline, RentalMovementInline] # 계약 안에서 자재목록과 입출고회차를 동시에 확인

@admin.register(RentalMovement)
class RentalMovementAdmin(admin.ModelAdmin):
    list_display = ['id', 'rental', 'movement_type', 'status', 'created_at']
    list_filter = ['movement_type', 'status']
    inlines = [MovementDetailInline] # 회차 상세 페이지에서 이동 자재 수량을 바로 확인

# 나머지 기본 등록
admin.site.register(Company)
admin.site.register(Site)
admin.site.register(User)
admin.site.register(SiteAssignment)
admin.site.register(Material)
admin.site.register(RentalDetail)
admin.site.register(RentalMovementDetail)
admin.site.register(AIRecognition)