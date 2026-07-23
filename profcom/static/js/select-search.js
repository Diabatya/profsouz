document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('select.select-search').forEach(function (select) {
    const wrapper = document.createElement('div');
    wrapper.className = 'select-search-wrapper';
    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(select);

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'form-control form-control-sm select-search-input';
    input.placeholder = 'Поиск...';
    wrapper.insertBefore(input, select);

    const options = Array.from(select.options).map(function (opt) {
      return { value: opt.value, text: opt.text, original: opt };
    });

    input.addEventListener('input', function () {
      const term = input.value.toLowerCase();
      select.innerHTML = '';
      options.forEach(function (item) {
        if (item.text.toLowerCase().includes(term)) {
          select.appendChild(item.original);
        }
      });
    });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
      }
    });
  });
});
