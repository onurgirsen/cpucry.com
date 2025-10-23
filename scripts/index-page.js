import { games } from './games-data.js';

const grid = document.querySelector('[data-games-grid]');
const template = document.getElementById('game-card');

const createLabel = (title) => {
  const cleaned = title.replace(/[^\p{L}\p{N}\s\-–—]/gu, '');
  const tokens = cleaned.split(/[\s\-–—]+/u).filter(Boolean);
  const initials = tokens
    .map((token) => {
      const match = token.match(/[\p{L}\p{N}]/u);
      return match ? match[0].toUpperCase() : '';
    })
    .join('');
  if (initials.length >= 2) {
    return initials.slice(0, 3);
  }
  const fallback = cleaned.replace(/[^\p{L}\p{N}]/gu, '').slice(0, 3).toUpperCase();
  return fallback || 'CPU';
};

games.forEach((game) => {
  const fragment = template.content.cloneNode(true);
  const thumb = fragment.querySelector('.thumb');
  const thumbLabel = fragment.querySelector('.thumb-label');
  const hiddenAlt = fragment.querySelector('.thumb-alt');
  const button = fragment.querySelector('.button');

  const hue = (game.id * 37) % 360;
  thumb.style.setProperty('--hue', hue);

  const url = game.href;
  thumb.href = url;
  button.href = url;
  button.textContent = game.title;

  thumbLabel.textContent = createLabel(game.title);
  hiddenAlt.textContent = `Stylised thumbnail for ${game.title}`;
  if (game.description) {
    thumb.title = game.description;
    button.title = game.description;
  }

  grid.appendChild(fragment);
});
