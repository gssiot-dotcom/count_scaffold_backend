#urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    LoginView,
    CompanyViewSet,
    SiteViewSet,  # 현장관리용
    UserViewSet,
    MaterialViewSet,
    RentalViewSet,
    RentalDetailViewSet,
    RentalMovementViewSet,
    AIRecognitionViewSet,  # AI 결과 DB 저장
    DetectAPIView, ReturnRequestViewSet,  # AI 판독 요청 뷰 추가
)

router = DefaultRouter()

router.register(r'companies', CompanyViewSet, basename='companies')
router.register(r'sites', SiteViewSet, basename='sites')  # 현장 목록 관리용
router.register(r'users', UserViewSet, basename='users')
router.register(r'materials', MaterialViewSet, basename='materials')
router.register(r'rentals', RentalViewSet, basename='rentals')
router.register(r'rental-details', RentalDetailViewSet, basename='rental-details')
router.register(r'movements', RentalMovementViewSet, basename='movements')
router.register(r'ai-recognitions', AIRecognitionViewSet, basename='ai-recognitions')
router.register(r'return-requests', ReturnRequestViewSet, basename='return-requests')


urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),
    path('detect/', DetectAPIView.as_view(), name='detect'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)