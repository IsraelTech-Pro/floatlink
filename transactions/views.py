from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from agents.models import Agent
from django.db.models import Q

from .models import Transaction


@login_required
def transaction_list(request):
    agent = get_object_or_404(Agent, user=request.user)
    txs = Transaction.objects.filter(Q(from_agent=agent) | Q(to_agent=agent)).order_by('-created_at')
    return render(request, 'transactions/list.html', {'transactions': txs})


@login_required
def transaction_detail(request, pk: int):
    agent = get_object_or_404(Agent, user=request.user)
    tx = get_object_or_404(Transaction, pk=pk)
    if tx.from_agent_id != agent.id and tx.to_agent_id != agent.id:
        raise Http404
    return render(request, 'transactions/detail.html', {'tx': tx})
