(function(){
  const saved=localStorage.getItem('ddc5i-theme')||'light';document.documentElement.dataset.theme=saved;
  window.toggleTheme=function(){const next=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=next;localStorage.setItem('ddc5i-theme',next)};
  window.confirmAction=function(message){return window.confirm(message||'Continue with this action?')};
  document.addEventListener('DOMContentLoaded',()=>{
    document.querySelectorAll('[data-auto-submit]').forEach(el=>el.addEventListener('change',()=>el.form.submit()));
    document.querySelectorAll('[data-kanban-task]').forEach(card=>{
      card.addEventListener('dragstart',e=>{e.dataTransfer.setData('text/plain',card.dataset.taskId);card.style.opacity='.55'});
      card.addEventListener('dragend',()=>card.style.opacity='1');
    });
    document.querySelectorAll('[data-kanban-column]').forEach(col=>{
      col.addEventListener('dragover',e=>e.preventDefault());
      col.addEventListener('drop',async e=>{e.preventDefault();const taskId=e.dataTransfer.getData('text/plain');const column=col.dataset.kanbanColumn;
        const csrf=document.querySelector('meta[name=csrf-token]')?.content||'';const res=await fetch(`/api/tasks/${taskId}/move`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({column})});
        if(res.ok){location.reload()}else{const d=await res.json();alert(d.detail||'Unable to move task')}
      });
    });
    document.querySelectorAll('[data-score]').forEach(input=>input.addEventListener('input',()=>{
      let total=0;document.querySelectorAll('[data-score]').forEach(i=>total+=Number(i.value||0)*Number(i.dataset.weight||0)/5);
      const el=document.getElementById('score-total');if(el)el.textContent=total.toFixed(1);
    }));
  });
})();
