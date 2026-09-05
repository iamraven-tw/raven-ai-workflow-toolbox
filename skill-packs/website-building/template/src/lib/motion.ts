// 共用動畫層：主題只在 HTML 上宣告 data-* 屬性，這裡統一用 Motion（MIT）執行。
// 全部尊重 prefers-reduced-motion；沒有 JavaScript 時內容照常顯示（見 global.css 的 js-motion 規則）。
import { animate, inView, scroll, stagger } from 'motion';

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const finePointer = window.matchMedia('(pointer: fine)').matches;
const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

type Variant = 'up' | 'fade' | 'blur' | 'scale' | 'clip' | 'left' | 'right';

/** 各種進場方式的起始狀態；結束狀態一律是原位、不透明、無模糊。 */
function keyframes(variant: Variant): Record<string, [string | number, string | number]> {
  switch (variant) {
    case 'fade':
      return { opacity: [0, 1] };
    case 'blur':
      return { opacity: [0, 1], filter: ['blur(14px)', 'blur(0px)'], transform: ['translateY(18px)', 'translateY(0px)'] };
    case 'scale':
      return { opacity: [0, 1], transform: ['scale(1.06)', 'scale(1)'] };
    case 'clip':
      return { opacity: [0, 1], transform: ['translateY(110%)', 'translateY(0%)'] };
    case 'left':
      return { opacity: [0, 1], transform: ['translateX(-32px)', 'translateX(0px)'] };
    case 'right':
      return { opacity: [0, 1], transform: ['translateX(32px)', 'translateX(0px)'] };
    default:
      return { opacity: [0, 1], transform: ['translateY(28px)', 'translateY(0px)'] };
  }
}

/** data-reveal：元素進入視窗時進場；data-reveal-delay 為毫秒。 */
function setupReveal(): void {
  const nodes = document.querySelectorAll<HTMLElement>('[data-reveal]');
  nodes.forEach((node) => {
    if (reduced) {
      node.classList.add('is-in');
      return;
    }
    inView(
      node,
      () => {
        const variant = (node.dataset.reveal || 'up') as Variant;
        const delay = Number(node.dataset.revealDelay || 0) / 1000;
        node.classList.add('is-in');
        animate(node, keyframes(variant), { duration: variant === 'clip' ? 1.1 : 0.9, delay, ease: EASE });
      },
      { margin: '0px 0px -12% 0px' },
    );
  });
}

/** data-reveal-stagger：容器進入視窗時，子元素依序進場；屬性值為每個子元素的間隔毫秒。 */
function setupStagger(): void {
  document.querySelectorAll<HTMLElement>('[data-reveal-stagger]').forEach((container) => {
    const children = Array.from(container.children) as HTMLElement[];
    if (reduced || children.length === 0) {
      container.classList.add('is-in');
      return;
    }
    inView(
      container,
      () => {
        const variant = (container.dataset.revealVariant || 'up') as Variant;
        const step = Number(container.dataset.revealStagger || 90) / 1000;
        container.classList.add('is-in');
        animate(children, keyframes(variant), { duration: 0.8, delay: stagger(step), ease: EASE });
      },
      { margin: '0px 0px -10% 0px' },
    );
  });
}

/** data-parallax：捲動時輕微位移，屬性值是速度（0.1 到 0.4 合理，負值反向）。 */
function setupParallax(): void {
  if (reduced) return;
  document.querySelectorAll<HTMLElement>('[data-parallax]').forEach((node) => {
    const speed = Number(node.dataset.parallax || 0.2);
    const distance = Math.round(speed * 240);
    scroll(animate(node, { transform: [`translateY(${-distance}px)`, `translateY(${distance}px)`] }, { ease: 'linear' }), {
      target: node,
      offset: ['start end', 'end start'],
    });
  });
}

/** data-marquee：複製 .t-marquee-track 一份做無縫跑馬燈；屬性值為一圈的毫秒數。 */
function setupMarquee(): void {
  document.querySelectorAll<HTMLElement>('[data-marquee]').forEach((zone) => {
    const track = zone.querySelector<HTMLElement>('.t-marquee-track');
    if (!track) return;
    const clone = track.cloneNode(true) as HTMLElement;
    clone.setAttribute('aria-hidden', 'true');
    clone.querySelectorAll('a, button').forEach((el) => el.setAttribute('tabindex', '-1'));
    track.after(clone);
    const duration = Number(zone.dataset.marquee || 30000) / 1000;
    zone.style.setProperty('--marquee-duration', `${duration}s`);
  });
}

/** data-pointer：把游標在元素內的相對位置寫進 --px／--py，給 CSS 做聚光燈或跟隨效果。 */
function setupPointer(): void {
  if (!finePointer) return;
  document.querySelectorAll<HTMLElement>('[data-pointer]').forEach((node) => {
    node.addEventListener('pointermove', (event) => {
      const rect = node.getBoundingClientRect();
      node.style.setProperty('--px', ((event.clientX - rect.left) / rect.width).toFixed(3));
      node.style.setProperty('--py', ((event.clientY - rect.top) / rect.height).toFixed(3));
    });
    node.addEventListener('pointerleave', () => {
      node.style.setProperty('--px', '0.5');
      node.style.setProperty('--py', '0.5');
    });
  });
}

/** data-trail：游標在區域內移動時，沿路留下會縮放、旋轉再消失的小圖片；只在精準指標裝置啟用。 */
function setupTrail(): void {
  if (!finePointer || reduced) return;
  document.querySelectorAll<HTMLElement>('[data-trail]').forEach((zone) => {
    const sources = (zone.dataset.trailImages || '').split(',').map((s) => s.trim()).filter(Boolean);
    const layer = zone.querySelector<HTMLElement>('[data-trail-layer]') ?? zone;
    if (sources.length === 0) return;
    let index = 0;
    let last = { x: -999, y: -999 };
    const alive: HTMLElement[] = [];
    zone.addEventListener('pointermove', (event) => {
      const rect = zone.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      if (Math.hypot(x - last.x, y - last.y) < 56) return;
      last = { x, y };
      const img = document.createElement('img');
      img.src = sources[index++ % sources.length];
      img.alt = '';
      img.className = 't-trail-img';
      img.style.left = `${x}px`;
      img.style.top = `${y}px`;
      const rotation = (Math.random() * 36 - 18).toFixed(1);
      layer.appendChild(img);
      alive.push(img);
      while (alive.length > 9) alive.shift()?.remove();
      animate(
        img,
        {
          opacity: [0, 1, 1, 0],
          transform: [
            `translate(-50%, -50%) scale(0.35) rotate(${rotation}deg)`,
            `translate(-50%, -50%) scale(1) rotate(${rotation}deg)`,
            `translate(-50%, -50%) scale(1) rotate(${rotation}deg)`,
            `translate(-50%, -50%) scale(0.5) rotate(${Number(rotation) * 3}deg)`,
          ],
        },
        { duration: 1.5, times: [0, 0.22, 0.7, 1], ease: 'easeOut' },
      ).finished.then(() => img.remove());
    });
  });
}

/** data-counter：元素文字裡的第一組數字從 0 數到目標值。 */
function setupCounter(): void {
  document.querySelectorAll<HTMLElement>('[data-counter]').forEach((node) => {
    const text = node.textContent ?? '';
    const match = text.match(/\d[\d,]*/);
    if (!match || reduced) return;
    const target = Number(match[0].replace(/,/g, ''));
    if (!Number.isFinite(target)) return;
    const [before, after] = [text.slice(0, match.index), text.slice((match.index ?? 0) + match[0].length)];
    inView(node, () => {
      animate(0, target, {
        duration: 1.6,
        ease: EASE,
        onUpdate: (value) => {
          node.textContent = `${before}${Math.round(value).toLocaleString('en-US')}${after}`;
        },
      });
    });
  });
}

/** data-split="words|chars"：把文字切成遮罩裡的小段，進入視窗時依序上升；data-split-step 為每段間隔毫秒。 */
function setupSplit(): void {
  document.querySelectorAll<HTMLElement>('[data-split]').forEach((node) => {
    if (node.classList.contains('is-split')) return;
    const mode = node.dataset.split === 'chars' ? 'chars' : 'words';
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
    const textNodes: Text[] = [];
    while (walker.nextNode()) {
      const current = walker.currentNode as Text;
      if (current.nodeValue && current.nodeValue.trim()) textNodes.push(current);
    }
    const pieces: HTMLElement[] = [];
    textNodes.forEach((textNode) => {
      const fragment = document.createDocumentFragment();
      const raw = textNode.nodeValue ?? '';
      // 中文沒有空格：words 模式下遇到沒有空白的長字串就退回逐字
      const tokens = mode === 'chars' || !/\s/.test(raw.trim()) ? Array.from(raw) : raw.split(/(\s+)/);
      tokens.forEach((token) => {
        if (!token) return;
        if (/^\s+$/.test(token)) {
          fragment.appendChild(document.createTextNode(token));
          return;
        }
        const mask = document.createElement('span');
        mask.className = 't-split-mask';
        const item = document.createElement('span');
        item.className = 't-split-item';
        item.textContent = token;
        mask.appendChild(item);
        fragment.appendChild(mask);
        pieces.push(item);
      });
      textNode.parentNode?.replaceChild(fragment, textNode);
    });
    node.classList.add('is-split');
    if (reduced || pieces.length === 0) {
      node.classList.add('is-in');
      return;
    }
    const step = Number(node.dataset.splitStep || 40) / 1000;
    inView(
      node,
      () => {
        node.classList.add('is-in');
        animate(pieces, { transform: ['translateY(110%)', 'translateY(0%)'], opacity: [0, 1] }, { duration: 0.8, delay: stagger(step), ease: EASE });
      },
      { margin: '0px 0px -10% 0px' },
    );
  });
}

/** data-magnet="x,y"：按鈕內的 [data-magnet-target] 會朝游標方向微微偏移（百分比），離開時回原位。 */
function setupMagnet(): void {
  if (!finePointer || reduced) return;
  document.querySelectorAll<HTMLElement>('[data-magnet]').forEach((node) => {
    const target = node.querySelector<HTMLElement>('[data-magnet-target]') ?? node;
    const [mx, my] = (node.dataset.magnet || '12,12').split(',').map(Number);
    node.addEventListener('pointermove', (event) => {
      const rect = node.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width - 0.5) * 2 * mx;
      const y = ((event.clientY - rect.top) / rect.height - 0.5) * 2 * my;
      target.style.translate = `${x.toFixed(2)}% ${y.toFixed(2)}%`;
    });
    node.addEventListener('pointerleave', () => {
      target.style.translate = '';
    });
  });
}

/** data-rotator：子元素 .t-rotator-item 一次只顯示一個；[data-rotator-prev]／[data-rotator-next] 切換，[data-rotator-count] 顯示序號；每 6 秒自動前進。 */
function setupRotator(): void {
  document.querySelectorAll<HTMLElement>('[data-rotator]').forEach((zone) => {
    const items = Array.from(zone.querySelectorAll<HTMLElement>('.t-rotator-item'));
    if (items.length === 0) return;
    const counter = zone.querySelector<HTMLElement>('[data-rotator-count]');
    let index = 0;
    const show = (next: number) => {
      index = (next + items.length) % items.length;
      items.forEach((item, position) => {
        const active = position === index;
        item.hidden = !active;
        item.setAttribute('aria-hidden', String(!active));
        if (active && !reduced) animate(item, { opacity: [0, 1], transform: ['translateY(10px)', 'translateY(0px)'] }, { duration: 0.6, ease: EASE });
      });
      if (counter) counter.textContent = `${index + 1} / ${items.length}`;
    };
    show(0);
    zone.querySelector('[data-rotator-prev]')?.addEventListener('click', () => show(index - 1));
    zone.querySelector('[data-rotator-next]')?.addEventListener('click', () => show(index + 1));
    if (items.length > 1 && !reduced) {
      let timer = window.setInterval(() => show(index + 1), 6000);
      zone.addEventListener('pointerenter', () => window.clearInterval(timer));
      zone.addEventListener('pointerleave', () => {
        timer = window.setInterval(() => show(index + 1), 6000);
      });
    }
  });
}

function init(): void {
  setupReveal();
  setupStagger();
  setupParallax();
  setupMarquee();
  setupPointer();
  setupTrail();
  setupCounter();
  setupSplit();
  setupMagnet();
  setupRotator();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init, { once: true });
} else {
  init();
}
