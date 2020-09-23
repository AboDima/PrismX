import ScoutView
import boto3
import datetime
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import *
from .config import updatejira,jiraconfig,testjira
import json
import datetime
import re
import difflib
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import exceptions, status
from rest_framework.views import APIView
from rest_framework import exceptions, status
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Min
from django.contrib.auth import admin as auth_admin, get_user_model
from django.db.models import F, Sum
from django.db.models.functions import TruncMonth, TruncDay, TruncDate
from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from django.db.models.functions import Trunc
from .serializers import *
from .models import *
from .tasks import runscan
from .tickets import *

User = get_user_model()

class AccountsDatatableListAPIView(ListAPIView):
    serializer_class = AccountSerializer

    def get_queryset(self):
        queryset = Account.objects.all().order_by('-id')
        return queryset

    def get(self, request, *args, **kwargs):

        draw = request.GET.get('draw')
        qs = self.get_queryset()
        account_qs_range = qs

        draw = request.GET.get('draw')
        records_total = qs.count()
        records_filtered = qs.count()

        length = int(request.GET.get('length'))
        start = int(request.GET.get('start'))
        order_column = request.GET.get('order[0][column]')
        order_dir = request.GET.get('order[0][dir]')
        search_str = request.GET.get('search[value]')

        page_num = int(request.GET.get('page_num', 1))

        column_names = [
            'nickname', 'account_id', 'last_scan_time', '',
        ]

        if search_str:
            account_qs_range = account_qs_range.filter(
                Q(nickname__icontains=search_str) |
                Q(account_id__icontains=search_str)
            )
            records_filtered = account_qs_range.count()

        if order_column:
            order_str = column_names[int(order_column)]
            if order_dir == 'desc':
                order_str = f'-{column_names[int(order_column)]}'

            account_qs_range = account_qs_range.order_by(order_str)
        # else:
        new_start = (page_num - 1) * length
        start = new_start if new_start <= records_filtered else start

        account_qs_range = account_qs_range[start:(start + length)]

        data_array = []
        for q in account_qs_range:
            data_array.append({
                'id': q.id,
                'nickname': q.nickname,
                'account_id': q.account_id,
                'last_scan_time': q.last_scan_time.strftime("%b %d, %Y %H:%M:%S"),
            })

        response = {
            'draw': draw,
            'recordsTotal': records_total,
            'recordsFiltered': records_filtered,
            'data': data_array
        }

        return Response(response, status=status.HTTP_200_OK)

class RunScanAPIView(APIView):
    def get(self, request):
        id = request.GET.get('id', None)

        if not id:
            raise exceptions.NotFound('ID is not provided')

        account = Account.objects.get(id=id)
        account.last_scan_time = timezone.now()
        account.save()

        runscan.delay(account.aws_access_key, account.aws_secret_key)

        response = {'status': 'success'}
        return Response(response, status=status.HTTP_200_OK)



def home(request):
    return render(request, 'core/index.html', context=ScoutView.View())

@login_required
def index(request):
    context = {
        'dashboard': 'active'
    }
    return render(request, 'index.html', context=ScoutView.View())


@login_required
def list(request):
    members_list = Member.objects.all()
    paginator = Paginator(members_list, 5)
    page = request.GET.get('page')
    try:
        members = paginator.page(page)
    except PageNotAnInteger:
        members = paginator.page(1)
    except EmptyPage:
        members = paginator.page(paginator.num_pages)
    return render(request, 'list.html', {'members': members})

@login_required
def create(request):
    if request.method == 'POST':
        member = Member(
            firstname=request.POST['firstname'],
            lastname=request.POST['lastname'],
            mobile_number=request.POST['mobile_number'],
            description=request.POST['description'],
            location=request.POST['location'],
            date=request.POST['date'],
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(), )
        try:
            member.full_clean()
        except ValidationError as e:
            pass
        member.save()
        messages.success(request, 'Member was created successfully!')
        return redirect('/list')
    else:
        return render(request, 'add.html')

@login_required
def edit(request, id):
    members = Member.objects.get(id=id)
    context = {'members': members}
    return render(request, 'edit.html', context)


@login_required
def update(request, id):
    member = Member.objects.get(id=id)
    member.firstname = request.POST['firstname']
    member.lastname = request.POST['lastname']
    member.mobile_number = request.POST['mobile_number'],
    member.description = request.POST['description'],
    member.location = request.POST['location'],
    member.date = request.POST['date'],
    member.save()
    messages.success(request, 'Member was updated successfully!')
    return redirect('/list')

@login_required
def delete(request, id):
    member = Member.objects.get(id=id)
    member.delete()
    messages.error(request, 'Member was deleted successfully!')
    return redirect('/list')

@csrf_protect
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password1'],
                is_staff=True,
                is_active=True,
                is_superuser=True,
                email=form.cleaned_data['email'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            )
            return HttpResponseRedirect('/register/success/')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

def register_success(request):
    return render(request, 'success.html')

@login_required
def users(request):
    users_list = User.objects.all()
    paginator = Paginator(users_list, 5)
    page = request.GET.get('page')
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)
    return render(request, 'users.html', {'users': users})

@login_required
def user_delete(request, id):
    user = User.objects.get(id=id)
    user.delete()
    messages.error(request, 'User was deleted successfully!')
    return redirect('/users')


@login_required
def changePassword(request):
    return render(request, 'change_password.html')

@login_required
def config(request):
    context = {
        'aws_account': 'active'
    }
    if request.method == 'POST':
        try:
            session = boto3.Session(aws_access_key_id=request.POST['access_key'],aws_secret_access_key=request.POST['secret_key'])
            sts_client = session.client('sts')
            account_id = sts_client.get_caller_identity()["Account"]
            if account_id in ScoutView.Accounts():
                messages.warning(request,'Account Already Exists')
            else:
                created = Account.objects.create(
                    user=request.user,
                    nickname=request.POST.get('nickname', ''),
                    aws_access_key=request.POST.get('access_key'),
                    aws_secret_key=request.POST.get('secret_key'),
                    account_id=account_id,
                    last_scan_time=timezone.now(),
                )
                runscan.delay(request.POST['access_key'],request.POST['secret_key'])
                messages.success(request, 'Credentials Valid!')
            return redirect('/config')
        except Exception as e:
            messages.warning(request, '%s' % e)
            return redirect('/config')

    return render(request, 'config.html', context=context)

@login_required
def jira(request):
    if request.method == 'POST':
        if 'test' in request.POST:
            try:
                testjira(request.POST['url'],request.POST['username'],request.POST['password'])
                messages.success(request, 'Credentials Valid!')
                return redirect('/jira')
            except Exception as e:
                messages.warning(request, '%s' % e)
                return redirect('/jira')
        else:
            try:
                updatejira(request.POST['url'],request.POST['username'],request.POST['password'])
                messages.success(request, 'JIRA Successfully Enabled')
                return redirect('/jira')
            except Exception as e:
                messages.warning(request, '%s' % e)
                return redirect('/jira')
    return render(request, 'jira.html',context=jiraconfig())

@login_required
def sso(request):
    if request.method == 'POST':
        if 'test' in request.POST:
            try:
                testjira(request.POST['url'],request.POST['username'],request.POST['password'])
                messages.success(request, 'Credentials Valid!')
                return redirect('/jira')
            except Exception as e:
                messages.warning(request, '%s' % e)
                return redirect('/jira')
        else:
            updatejira(request.POST['url'],request.POST['username'],request.POST['password'])
            return redirect('/jira')
    return render(request, 'sso.html')


def getaccount(request, account):
    return render(request, 'account.html',context=ScoutView.View(account))


def accountservice(request, service, account):
    if request.method == "POST":
        try:
            newticket = issue(request.POST['board'],request.POST['title'],request.POST['description'])
            messages.success(request,'JIRA Created: %s' % newticket)
        except Exception as e:
            messages.warning(request,'%s' % e)
    return render(request, 'findings.html',context={"service":service,"response":ScoutView.Service(service,account)})


def service(request, service):
    if request.method == "POST":
        try:
            newticket = issue(request.POST['board'],request.POST['title'],request.POST['description'])
            messages.success(request,'JIRA Created: %s' % newticket)
        except Exception as e:
            messages.warning(request,'%s' % e)
    return render(request, 'findings.html',context={"service":service,"response":ScoutView.Service(service,"")})

def getreport(request, report):
    return render(request,'report.html',context=ScoutView.Report(report))


def parsereport(request):
    if request.method == "PUT":
        ScoutView.ParseReport(request.body)
    return HttpResponse(status=201)
