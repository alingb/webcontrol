# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import time

from django.contrib.auth.decorators import login_required

from saltstack import SaltApi
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render
from web.models import *


# Create your views here.




@login_required
def index(req):
    totalNum = Host.objects.count()
    runNum = Host.objects.filter(stress_test="running").count()
    stopNum = Host.objects.filter(Q(stress_test="reload")).count()
    offNum = Host.objects.filter(status__contains="erro").count()
    form = Stat.objects.all()
    count = form.count()
    form = form.order_by('-status', 'hostname')
    a = 1
    for i in form:
        b = i
        b.num = a
        a += 1
        b.save()
    num = []
    for i in form:
        if 'OS off' in i.status:
            num.append(i.status[:-6])
        else:
            num.append(i.status)
    dic = {}
    data = set(num)
    for i in data:
        dic[i] = num.count(i)
    strs = ""
    for k, v in dic.items():
        strs += '--"%s"(%s)--' % (k, v)
    return render(req, 'index.html', {'totalNum': totalNum, 'runNum': runNum, 'offNum': offNum, "stopNum": stopNum,
                                      'form': form, 'count': count, 'dic': strs})


@login_required
def serverDetail(req):
    global name, status
    name = req.GET.get("name")
    status = req.GET.get("status")
    return render(req, 'serverdetail.html')


@login_required
def bios(req):
    Bios = {1: "D51B-2U",
            2: "T41S-2U",
            3: "ASR1100",
            4: "RS100-E9-PI2",
            5: "RS300-E9-PS4",
            6: "RS720Q-E8",
            7: "ESC8000G3",
            8: "P10S-M-DC",
            9: "Z10PA-D8",
            10: "K880G3",
            11: "N880G2",
            12: "SR205-2"
            }
    return render(req, 'bios.html', {"bios": Bios})


@login_required
def execute(req):
    return render(req, 'execute.html')


@login_required
def serverInfo(request):
    global name, status
    limit = request.GET.get("limit")
    offset = request.GET.get("offset")
    search = request.GET.get("search")
    state = request.GET.get("state")
    sort = request.GET.get("sort")
    sortOrder = request.GET.get("sortOrder")
    host = ''
    try:
        if name and status:
            if name == "run":
                host = Host.objects.filter(stress_test=status)
            elif name == "error":
                host = Host.objects.filter(status__contains=status)
            name, status = '', ''
    except Exception:
        pass
    if not host:
        host = Host.objects.all()
    if state:
        host = host.filter(stress_test=state)
    if search:
        host = host.filter(Q(sn__contains=search) |
                           Q(sn_1__contains=search) |
                           Q(name1__contains=search) |
                           Q(name__contains=search) |
                           Q(family__contains=search) |
                           Q(status__contains=search) |
                           Q(ip__contains=search))
    lenth = host.count()
    if sort and sortOrder:
        if sortOrder == "asc":
            host = host.order_by("{}".format(sort))
        elif sortOrder == "desc":
            host = host.order_by("-{}".format(sort))
    if offset and limit:
        offset = int(offset)
        limit = int(limit)
        host = host[offset:offset + limit]
    data = []
    for each in host:
        data.append(model_to_dict(each, fields=['id', 'sn', 'sn_1', 'name', 'name1', 'family',
                                                'status', 'bios', 'bmc', 'ip', 'stress_test']))
    return HttpResponse(json.dumps({"rows": data, "total": lenth}))


@login_required
def control(req):
    salt_api = "https://127.0.0.1:8000/"
    Salt = SaltApi(salt_api)
    state = req.POST.get('state')
    name = req.POST.get('name')
    file = req.FILES.get('fru_sn')
    if state == "bios":
        cmd = '/bios/{}/BIOS_lnx64.sh'.format(name)
        msg = req.POST.get('msg')
        if msg:
            msg = json.loads(msg)
            for each in msg:
                Salt.cmd('{}'.format(each['ip']), 'cmd.run', ['{}'.format(cmd)])
                time.sleep(10)
    elif state == "bmc":
        cmd = '/bmc/{}/BMC_lnx64.sh'.format(name)
        msg = req.POST.get('msg')
        if msg:
            msg = json.loads(msg)
            for each in msg:
                Salt.cmd('{}'.format(each['ip']), 'cmd.run', ['{}'.format(cmd)])
    elif file:
        sn = file.readlines()
        msg = req.POST.get('msg')
        fru_name = req.POST.get('fru_name')
        num = 0
        if msg:
            msg = json.loads(msg)
            if len(msg) != len(sn):
                return HttpResponseBadRequest()
            for each in msg:
                print each['ip'], sn[num].strip()
                cmd = 'echo "{}" | /fru/{}/FRU_lnx64.sh'.format(sn[num].strip(), fru_name)
                num += 1
                print cmd
                try:
                    Salt.cmd('{}'.format(each['ip']), 'cmd.run', ['{}'.format(cmd)])
                except Exception:
                    pass
        return HttpResponseRedirect('/control/bios')
    elif state == "run":
        msg = req.POST.get('msg')
        info = req.POST.get('info')
        if info and msg:
            info = json.loads(info)
            msg = json.loads(msg)
            for each in msg:
                for i in info:
                    Salt.cmd('{}'.format(each['ip']), 'service.start', ['{}'.format(i.lower())])
                    print each['ip'], i
    return HttpResponse()


@login_required
def infoPaser(req):
    val = str(req.POST.get('val'))
    if val:
        if val.isdigit():
            val = int(val)
    name_list = {
        1: ["SunMnet-M3", "UDS1022"],
        2: ["UDS2000-C", "UDS2000-E", "zhongdianfufu"],
        3: ['RG-eLog', 'RCP', 'meidian'],
        4: ['RG-RCP1.0'],
        5: ['RG-RCM1000-Office', 'RG-RCM1000-Smart', 'RG-RCM1000-Edu'],
        6: ['RG-ONC-AIO-CTL'],
        7: ['RG-RCD16000Pro-3D'],
        8: ['P10S-M-DC'],
        9: ['tianrongxin'],
        10: ['RG-RCD6000-Main', 'RG-RCD6000-Office', 'RG-iData-Server', 'RG-RACC5000', 'RG-RCD3000-Office', 'RG-RCD6000EV3', 'haiyunjiexun'],
        11: ['Meidian'],
        12: ['DT-G2-U211', 'CZ-2U-K888G4'],
    }
    return HttpResponse(json.dumps(name_list[val]))


def controlDeatil(req, ID):
    form = Host.objects.get(id=ID)
    message = form.message
    dic = {}
    import re
    ALL_LIST = []
    for i in message.split('\n'):
        re_info = re.findall(r'(^[A-Z]{1,8}[\s_]*[A-Z1-9]*):', i, re.M)
        if re_info:
            ALL_LIST.append(re_info[0])
    for i in xrange(len(ALL_LIST)):
        try:
            info = message.split(ALL_LIST[i+1])[0].strip()
            split_info = ALL_LIST[i] +  ':'
            try:
                data = info.split(split_info)[1].strip()
            except:
                data = ''
            dic[ALL_LIST[i].replace(' ', '_')] = data.strip()
        except:
            info = message.split(ALL_LIST[i])[0]
            dic[ALL_LIST[i].replace(' ', '_')] = info.split(':')[1]
    return render(req, 'detail.html', {'form': dic, 'all': form})
