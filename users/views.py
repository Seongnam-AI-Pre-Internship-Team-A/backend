from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.core.cache import cache
# Create your views here.
from django.urls import reverse
from requests import Response
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from datetime import datetime, timedelta
from .models import user
from .serializers import UserSerializer, CustomRegisterSerializer

# 누구나 접근 가능 (회원가입 , 아이디 중복시 Error 반환하도록 설계 필요)
from .utils import user_find_by_name, user_comppassword, user_generate_access_token, user_generate_refresh_token, \
    user_find_by_email, UserDuplicateCheck, user_token_to_data, user_refresh_to_access


@permission_classes([AllowAny])
class create(generics.GenericAPIView):
    serializer_class = CustomRegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=True):
            return Response({"message": "Request Body Error."}, status=status.HTTP_409_CONFLICT)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()  # request 필요 -> 오류 발생 //
        return HttpResponse(status=200)


# Login
def login(request):
    input_email = request.data['email']
    input_password = request.data['password']
    access_token = None
    refresh_token = None

    if input_password and input_email:
        user_data = user_find_by_email(input_email).first()
        if user_data:
            if user_comppassword(input_password, user_data):
                access_token = user_generate_access_token(user_data)
                refresh_token = user_generate_refresh_token(user_data)
        else:
            return JsonResponse({"message": "invalid_data"}, status=400)

    data = {"access_token": access_token, "refresh_token": refresh_token,
            "expiredTime": datetime.utcnow() + timedelta(minutes=30),
            "email": user_data.email}

    return JsonResponse({"result": data}, status=200)


# ID duplication check
def user_is_duplicate(request):
    email = request.GET.get('email')

    emailValidation=UserDuplicateCheck().email(email)

    if(emailValidation):
        return JsonResponse({"message": "Invalid value"}, status=401)
    return JsonResponse({"result": emailValidation}, status=200)



# refreshtoken 재발급
def user_reissuance_access_token(request):
    token = request.headers.get('Authorization', None)
    payload = user_token_to_data(token)
    if payload:
        # new access_token 반환
        if payload.get('type') == 'refresh_token':
            access_token = user_refresh_to_access(token)
            return JsonResponse({"access_token": access_token,
                                 "expiredTime": datetime.utcnow() + timedelta(minutes=30)}, status=200)
        else:
            return JsonResponse({"message": "Not refresh_token"}, status=401)
    else:
        return JsonResponse({"message": payload}, status=401)