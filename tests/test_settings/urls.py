from django.conf.urls import include, url

urlpatterns = [
    url(r'^anymail/', include('anymail.urls')),
]
