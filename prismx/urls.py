from . import views
from django.conf.urls import url
from django.conf.urls import url,include
from django.views.decorators.csrf import csrf_exempt
from django.urls import path, include

from .views import AccountsDatatableListAPIView, RunScanAPIView


urlpatterns = [
    # url(r'^$', home, name='home'),
    url(r'^account/(?P<account>\d+)/$',views.getaccount, name='account'),
    url(r'^service/(?P<service>\w+)/$', views.service, name='service'),
    url(r'^^account/(?P<account>\d+)/service/(?P<service>\w+)/$', views.accountservice, name='service'),
    url(r'^report/(?P<report>\d+)/', views.getreport, name='report'),
    url(r'upload$',csrf_exempt(views.parsereport), name='parsereport'),
     url(r'^$', views.index, name='index'),
    url(r'^create$', views.create, name='create'),
    url(r'^list$', views.list, name='list'),
    url(r'^edit/(?P<id>\d+)$', views.edit, name='edit'),
    url(r'^edit/update/(?P<id>\d+)$', views.update, name='update'),
    url(r'^delete/(?P<id>\d+)$', views.delete, name='delete'),
    url(r'^register/$', views.register,name='register'),
    url(r'^register/success/$',views.register_success,name='register_success'),
    url(r'^users/$',views.users,name='users'),
    url(r'^users/delete/(?P<id>\d+)$', views.user_delete, name='user_delete'),
    url(r'^user/settings$', views.changePassword, name='changePassword'),
    url(r'^jira$', views.jira, name='jira'),
    url(r'^sso$', views.sso, name='sso'),
    url(r'^config$', views.config, name='config'),
    path('account-list/', AccountsDatatableListAPIView.as_view(), name='account-list'),
    path('run-scan/', RunScanAPIView.as_view(), name='run-scan'),
]