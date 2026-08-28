/* ============================================================
   GIX in Seattle — 互動腳本

   載入位置：</body> 之前，且必須排在 Bootstrap bundle 後面，
   因為會用到 bootstrap.Collapse 與 bootstrap.Offcanvas。
   放在 body 結尾表示執行時 DOM 已經備妥，
   所以不需要再包一層 DOMContentLoaded。
   ============================================================ */


/* ============================================================
   1. 卡片 → 視窗
   ============================================================ */
const topicModal = document.getElementById('topicModal');

topicModal.addEventListener('show.bs.modal', event => {
  const card = event.relatedTarget;
  topicModal.querySelector('.modal-title').textContent = card.dataset.title;

  const imgCol  = topicModal.querySelector('.modal-img-col');
  const textCol = topicModal.querySelector('.modal-text');
  const wide    = card.dataset.layout === 'wide';

  // 圖多的篇章用滿版，封面圖就不另外顯示
  imgCol.classList.toggle('d-none', wide);
  textCol.classList.toggle('col-md-7', !wide);
  textCol.classList.toggle('col-12', wide);

  if (!wide) {
    const img = topicModal.querySelector('.modal-img');
    img.src = card.dataset.img;
    img.alt = card.dataset.title;
  }

  const source = document.querySelector(card.dataset.body);
  textCol.innerHTML = source ? source.innerHTML : '';
});

// 卡片是 <article> 不是 <button>，鍵盤操作要自己補
document.querySelectorAll('.topic-card').forEach(card => {
  card.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      card.click();
    }
  });
});


/* ============================================================
   2. 暴雷遮蔽：點一下顯示
   用事件委派，所以視窗裡動態塞進來的內容也有效
   ============================================================ */
document.addEventListener('click', e => {
  const t = e.target.closest('.spoiler, .spoiler-blur, .spoiler-img');
  if (!t || t.classList.contains('revealed')) return;
  t.classList.add('revealed');
  if (t.hasAttribute('aria-expanded')) t.setAttribute('aria-expanded', 'true');
});


/* ============================================================
   3. 導覽列的小飛機：停在目前展開的那一區
   ============================================================ */
const tocNav       = document.getElementById('tocNav');
const tocPlane     = document.getElementById('tocPlane');
const tocOffcanvas = document.getElementById('tocOffcanvas');
const fabLabel     = document.querySelector('.toc-fab-label');
const softMotion   = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;

let planeY = null;

function flyTo(link) {
  if (!link) return;
  const y = link.offsetTop + link.offsetHeight / 2;
  const goingDown = planeY === null || y >= planeY;
  planeY = y;
  tocPlane.style.top = y + 'px';
  tocPlane.style.setProperty('--plane-rotate', goingDown ? '180deg' : '0deg');
}

function currentLink() {
  const open = document.querySelector('.section-accordion .accordion-collapse.show');
  const id = open ? open.id.replace('panel-', '') : null;
  return (id && tocNav.querySelector('[href="#' + id + '"]')) || tocNav.querySelector('.nav-link');
}

function syncPlane() {
  const link = currentLink();
  tocNav.querySelectorAll('.nav-link').forEach(a => a.classList.toggle('active', a === link));
  flyTo(link);
  if (fabLabel && link) fabLabel.textContent = link.textContent.trim();
}

// 點導覽列 → 展開那一區並捲過去
tocNav.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const id = link.getAttribute('href').slice(1);
    const panel = document.getElementById('panel-' + id);
    bootstrap.Collapse.getOrCreateInstance(panel, { toggle: false }).show();

    // 手機版：選完就把面板收起來，收完再捲過去
    const oc = bootstrap.Offcanvas.getInstance(tocOffcanvas);
    const goThere = () => document.getElementById(id).scrollIntoView({
      behavior: softMotion ? 'smooth' : 'auto',
      block: 'start'
    });

    if (oc && tocOffcanvas.classList.contains('show')) {
      tocOffcanvas.addEventListener('hidden.bs.offcanvas', goThere, { once: true });
      oc.hide();
    } else {
      goThere();
    }
  });

  // 滑過去先預覽，移開再飛回目前展開的區塊
  link.addEventListener('mouseenter', () => flyTo(link));
  link.addEventListener('focus', () => flyTo(link));
});

tocNav.addEventListener('mouseleave', syncPlane);

// 展開／收合任一區塊時，飛機跟著走
document.getElementById('mainAccordion')
  .addEventListener('shown.bs.collapse', syncPlane);
document.getElementById('mainAccordion')
  .addEventListener('hidden.bs.collapse', syncPlane);

// 面板藏起來時算不出位置，等它出現再定位飛機
tocOffcanvas.addEventListener('shown.bs.offcanvas', () => {
  planeY = null;          // 重新出現時不要播放飛行動畫
  syncPlane();
  document.body.classList.add('offcanvas-open');
});

tocOffcanvas.addEventListener('hidden.bs.offcanvas', () => {
  document.body.classList.remove('offcanvas-open');
});

window.addEventListener('resize', syncPlane);
syncPlane();
