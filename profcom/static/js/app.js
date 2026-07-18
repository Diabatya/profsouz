(function(){
  'use strict';

  function ready(fn){
    if(document.readyState !== 'loading'){
      fn();
    } else {
      document.addEventListener('DOMContentLoaded', fn);
    }
  }

  // Autofill amount when payout type / category changes
  ready(function(){
    var typeSelect = document.getElementById('type_id');
    var amountInput = document.getElementById('amount');
    var categorySelect = document.getElementById('category_id');
    if(typeSelect && amountInput && categorySelect && window.PAYOUT_CATEGORIES){
      var categories = window.PAYOUT_CATEGORIES;
      function getDataset(el){ return el && el.options[el.selectedIndex] ? el.options[el.selectedIndex].dataset : {}; }
      function updateCategories(){
        var typeId = parseInt(typeSelect.value) || 0;
        var selectedCat = parseInt(categorySelect.dataset.selectedCategory) || 0;
        categorySelect.innerHTML = '<option value="">-</option>';
        categories.forEach(function(c){
          if(c.type_id == typeId){
            var opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            opt.dataset.amount = c.amount;
            if(c.id == selectedCat) opt.selected = true;
            categorySelect.appendChild(opt);
          }
        });
      }
      function updateAmount(){
        var catOption = categorySelect.options[categorySelect.selectedIndex];
        if(catOption && catOption.value && catOption.dataset.amount){
          amountInput.value = catOption.dataset.amount;
        } else {
          var typeOption = typeSelect.options[typeSelect.selectedIndex];
          if(typeOption && typeOption.dataset.amount) amountInput.value = typeOption.dataset.amount;
        }
      }
      typeSelect.addEventListener('change', function(){
        updateCategories();
        updateAmount();
      });
      categorySelect.addEventListener('change', updateAmount);
      updateCategories();
    } else if(typeSelect && amountInput){
      typeSelect.addEventListener('change', function(){
        var option = typeSelect.options[typeSelect.selectedIndex];
        if(option && option.dataset.amount){
          amountInput.value = option.dataset.amount;
        }
      });
    }
  });

  // Event expenses: add / remove rows and recalc total
  ready(function(){
    var container = document.getElementById('expenses-container');
    var addBtn = document.getElementById('add-expense');
    var totalEl = document.getElementById('total-expenses');

    function recalc(){
      var total = 0;
      container.querySelectorAll('.expense-amount').forEach(function(input){
        var v = parseFloat(input.value.replace(',', '.'));
        if(!isNaN(v)) total += v;
      });
      if(totalEl) totalEl.textContent = total.toFixed(2) + ' ₽';
    }

    if(addBtn && container){
      addBtn.addEventListener('click', function(){
        var row = document.createElement('div');
        row.className = 'row g-2 mb-2 expense-row';
        row.innerHTML =
          '<div class="col-7"><input type="text" name="article[]" class="form-control form-control-sm" list="event-articles" placeholder="Статья" required></div>' +
          '<div class="col-4"><input type="number" step="0.01" name="amount[]" class="form-control form-control-sm expense-amount" placeholder="0.00" required></div>' +
          '<div class="col-1"><button type="button" class="btn btn-outline-danger btn-sm w-100 remove-expense">&times;</button></div>';
        container.appendChild(row);
        row.querySelector('.expense-amount').addEventListener('input', recalc);
        row.querySelector('.remove-expense').addEventListener('click', function(){
          row.remove();
          recalc();
        });
      });

      container.addEventListener('input', function(e){
        if(e.target.classList.contains('expense-amount')) recalc();
      });

      container.querySelectorAll('.remove-expense').forEach(function(btn){
        btn.addEventListener('click', function(){
          btn.closest('.expense-row').remove();
          recalc();
        });
      });
    }
  });

  // Event helpers: add / remove rows
  ready(function(){
    var container = document.getElementById('helpers-container');
    var addBtn = document.getElementById('add-helper');
    var source = document.getElementById('helper-template');

    if(addBtn && container && source){
      addBtn.addEventListener('click', function(){
        var row = document.createElement('div');
        row.className = 'row g-2 mb-2 helper-row';
        row.innerHTML = source.innerHTML;
        container.appendChild(row);
        row.querySelector('.remove-helper').addEventListener('click', function(){
          row.remove();
        });
      });

      container.addEventListener('click', function(e){
        if(e.target.classList.contains('remove-helper')){
          e.target.closest('.helper-row').remove();
        }
      });
    }
  });

  // Delete confirmation for forms
  ready(function(){
    document.querySelectorAll('form.delete-form').forEach(function(form){
      form.addEventListener('submit', function(e){
        if(!confirm('Вы уверены, что хотите удалить эту запись?')){
          e.preventDefault();
        }
      });
    });
  });

  // Bootstrap tooltips
  ready(function(){
    if(typeof bootstrap !== 'undefined' && bootstrap.Tooltip){
      var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
      tooltipTriggerList.map(function(el){ return new bootstrap.Tooltip(el); });
    }
  });

  // Back to top button
  ready(function(){
    var btn = document.getElementById('backToTop');
    if(btn){
      window.addEventListener('scroll', function(){
        if(window.scrollY > 300){
          btn.classList.remove('d-none');
        } else {
          btn.classList.add('d-none');
        }
      });
      btn.addEventListener('click', function(){
        window.scrollTo({top: 0, behavior: 'smooth'});
      });
    }
  });

  // Bulk operations: select all and collect selected IDs
  ready(function(){
    var selectAll = document.getElementById('select-all');
    var bulkForm = document.getElementById('bulk-form');
    var bulkAction = document.getElementById('bulk-action');
    var bulkValueWrapper = document.getElementById('bulk-value-wrapper');

    function updateBulkValueField(){
      if(!bulkValueWrapper) return;
      var action = bulkAction ? bulkAction.value : '';
      if(action === 'change_gender'){
        bulkValueWrapper.innerHTML = '<label class="form-label small text-muted mb-1">Значение</label><select name="value" class="form-select"><option value="male">Мужской</option><option value="female">Женский</option></select>';
      } else {
        bulkValueWrapper.innerHTML = '<label class="form-label small text-muted mb-1">Значение</label><input type="text" name="value" class="form-control" placeholder="для отдела или должности">';
      }
    }

    if(bulkAction){
      bulkAction.addEventListener('change', updateBulkValueField);
      updateBulkValueField();
    }

    if(selectAll){
      selectAll.addEventListener('change', function(){
        document.querySelectorAll('.member-check').forEach(function(cb){
          cb.checked = selectAll.checked;
        });
      });
    }
    if(bulkForm){
      bulkForm.addEventListener('submit', function(e){
        var ids = [];
        document.querySelectorAll('.member-check:checked').forEach(function(cb){
          ids.push(cb.value);
        });
        if(ids.length === 0){
          alert('Выберите хотя бы одного члена');
          e.preventDefault();
          return false;
        }
        document.getElementById('bulk-ids').value = ids.join(',');
      });
    }
  });

  // Progress bars with data-width
  ready(function(){
    document.querySelectorAll('[data-width]').forEach(function(el){
      if(el.classList.contains('progress-bar')){
        el.style.width = el.getAttribute('data-width') + '%';
      }
    });
  });

  // Live search in members list: server-side DB-level search
  ready(function(){
    var searchInput = document.getElementById('live-search');
    if(searchInput){
      var timer;
      searchInput.addEventListener('input', function(){
        clearTimeout(timer);
        timer = setTimeout(function(){
          var q = searchInput.value.trim();
          var url = new URL(window.location.href);
          url.searchParams.delete('page');
          if(q){
            url.searchParams.set('search', q);
          } else {
            url.searchParams.delete('search');
          }
          window.location.href = url.toString();
        }, 500);
      });
    }
  });
})();
