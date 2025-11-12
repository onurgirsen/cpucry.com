(function () {
  const configEl = document.getElementById('game-config');
  const canvas = document.getElementById('field');
  if (!configEl || !canvas) {
    return;
  }

  let config;
  try {
    config = JSON.parse(configEl.textContent || '{}');
  } catch (err) {
    console.error('Failed to parse game config', err);
    return;
  }

  const ctx = canvas.getContext('2d');
  const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
  let width = window.innerWidth;
  let height = window.innerHeight;
  let backgroundGradient;

  function hexToRgb(hex) {
    if (!hex) return { r: 14, g: 20, b: 48 };
    const value = hex.replace('#', '');
    const bigint = parseInt(value, 16);
    if (Number.isNaN(bigint)) {
      return { r: 14, g: 20, b: 48 };
    }
    return {
      r: (bigint >> 16) & 255,
      g: (bigint >> 8) & 255,
      b: bigint & 255,
    };
  }

  function mixColor(a, b, t) {
    return {
      r: Math.round(a.r * (1 - t) + b.r * t),
      g: Math.round(a.g * (1 - t) + b.g * t),
      b: Math.round(a.b * (1 - t) + b.b * t),
    };
  }

  function rgbToCss(rgb, alpha = 1) {
    return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;
  }

  const colorConfig = config.colors || {};
  const colors = {
    background: hexToRgb(colorConfig.background || '#0b1026'),
    glow: hexToRgb(colorConfig.glow || '#6aa9ff'),
    spark: hexToRgb(colorConfig.spark || '#8ccfff'),
    trail: colorConfig.trail || 'rgba(12, 18, 32, 0.08)',
  };

  const particleDefaults = {
    initialCount: 220,
    maxCount: 1200,
    speed: 0.9,
    jitter: 0.3,
    burst: 200,
    drag: 0.02,
    gravity: 0.05,
    glow: 0.6,
    pointerForce: 0.8,
  };

  const intensityDefaults = {
    min: 0.3,
    max: 3.4,
    step: 0.1,
    initial: 1.2,
  };

  const options = Object.assign({}, particleDefaults, config.particle || {});
  const intensity = Object.assign({}, intensityDefaults, config.intensity || {});
  let intensityFactor = intensity.initial;

  const slider = document.getElementById('intensity');
  if (slider) {
    slider.min = String(intensity.min);
    slider.max = String(intensity.max);
    slider.step = String(intensity.step);
    slider.value = String(intensity.initial);
  }
  const sliderLabel = slider ? slider.parentElement.querySelector('span') : null;
  function updateSliderLabel(value) {
    if (sliderLabel) {
      sliderLabel.textContent = `Intensity ${value.toFixed(1)}×`;
    }
  }
  updateSliderLabel(intensityFactor);

  const burstButton = document.getElementById('burstButton');
  const freezeButton = document.getElementById('freezeButton');
  const clearButton = document.getElementById('clearButton');
  const countStat = document.getElementById('countStat');
  const fpsStat = document.getElementById('fpsStat');

  const pointer = {
    x: width / 2,
    y: height / 2,
    vx: 0,
    vy: 0,
    strength: 0,
    down: false,
    lastTime: performance.now(),
  };

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    backgroundGradient = ctx.createLinearGradient(0, 0, width, height);
    const lighten = mixColor(colors.background, colors.glow, 0.2);
    const deepen = mixColor(colors.background, { r: 4, g: 8, b: 20 }, 0.35);
    backgroundGradient.addColorStop(0, rgbToCss(lighten));
    backgroundGradient.addColorStop(0.45, rgbToCss(colors.background));
    backgroundGradient.addColorStop(1, rgbToCss(deepen));
    ctx.fillStyle = backgroundGradient;
    ctx.fillRect(0, 0, width, height);
  }

  resize();
  window.addEventListener('resize', resize);

  function pointerMove(event) {
    const now = performance.now();
    const dt = Math.max(16, now - pointer.lastTime);
    const prevX = pointer.x;
    const prevY = pointer.y;
    pointer.x = event.clientX;
    pointer.y = event.clientY;
    pointer.vx = ((pointer.x - prevX) / dt) * 1000;
    pointer.vy = ((pointer.y - prevY) / dt) * 1000;
    pointer.lastTime = now;
    pointer.strength = 1;
  }

  canvas.addEventListener('pointerdown', (event) => {
    pointer.down = true;
    pointerMove(event);
    canvas.setPointerCapture(event.pointerId);
  });

  canvas.addEventListener('pointermove', (event) => {
    pointerMove(event);
  });

  canvas.addEventListener('pointerup', (event) => {
    pointer.down = false;
    pointerMove(event);
    pointer.strength = Math.max(pointer.strength, 0.4);
    try {
      canvas.releasePointerCapture(event.pointerId);
    } catch (err) {
      // ignore
    }
  });

  canvas.addEventListener('pointerleave', () => {
    pointer.down = false;
  });

  if (slider) {
    slider.addEventListener('input', () => {
      const value = parseFloat(slider.value);
      if (!Number.isNaN(value)) {
        intensityFactor = value;
        updateSliderLabel(value);
      }
    });
  }

  let particles = [];

  function createParticle(atPointer = false) {
    const angle = Math.random() * Math.PI * 2;
    const radial = Math.pow(Math.random(), 0.6);
    const radius = radial * Math.max(width, height) * 0.45;
    const speedBase = (options.speed + Math.random() * options.jitter) * 120;
    const spawnSpread = atPointer && (pointer.down || pointer.strength > 0.2);
    const px = spawnSpread
      ? pointer.x + (Math.random() - 0.5) * 110
      : width / 2 + Math.cos(angle) * radius;
    const py = spawnSpread
      ? pointer.y + (Math.random() - 0.5) * 110
      : height / 2 + Math.sin(angle) * radius;

    return {
      x: px,
      y: py,
      vx: Math.cos(angle) * speedBase,
      vy: Math.sin(angle) * speedBase,
      life: 0,
      maxLife: 6 + Math.random() * 9,
      size: 0.7 + Math.random() * 2.8,
      energy: Math.random(),
      hue: Math.random() * Math.PI * 2,
    };
  }

  function spawnParticles(count, atPointer = false) {
    for (let i = 0; i < count; i += 1) {
      if (particles.length >= options.maxCount) {
        break;
      }
      particles.push(createParticle(atPointer));
    }
  }

  spawnParticles(options.initialCount);

  if (burstButton) {
    burstButton.addEventListener('click', () => {
      spawnParticles(options.burst, true);
    });
  }

  let frozen = false;
  if (freezeButton) {
    freezeButton.addEventListener('click', () => {
      frozen = !frozen;
      freezeButton.textContent = frozen ? 'Resume' : 'Freeze';
    });
  }

  if (clearButton) {
    clearButton.addEventListener('click', () => {
      particles = [];
      ctx.fillStyle = backgroundGradient;
      ctx.fillRect(0, 0, width, height);
    });
  }

  function drawParticle(p, fade) {
    const glowStrength = options.glow * (0.6 + p.energy * 0.8) * (0.6 + intensityFactor * 0.25);
    ctx.save();
    ctx.beginPath();
    ctx.shadowBlur = 18 * glowStrength;
    ctx.shadowColor = rgbToCss(colors.glow, 0.45 + fade * 0.4);
    const size = p.size * (0.7 + intensityFactor * 0.25) * (0.6 + fade * 0.6);
    ctx.fillStyle = rgbToCss(colors.spark, 0.35 + fade * 0.55);
    ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  function updateParticle(p, dt, frameTick) {
    const pointerActive = pointer.down || pointer.strength > 0.12;
    const pointerForce = options.pointerForce * 220 * intensityFactor;
    if (pointerActive) {
      const dx = pointer.x - p.x;
      const dy = pointer.y - p.y;
      const dist = Math.hypot(dx, dy) + 1;
      const force = pointerForce * (pointer.down ? 1.35 : 0.7);
      p.vx += (dx / dist) * force * dt;
      p.vy += (dy / dist) * force * dt;
      p.vx += pointer.vx * 0.18 * dt;
      p.vy += pointer.vy * 0.18 * dt;
    }

    const cx = width / 2;
    const cy = height / 2;
    const dx = p.x - cx;
    const dy = p.y - cy;
    const distCenter = Math.hypot(dx, dy) + 1;
    const swirlAmount = 60 * intensityFactor;

    switch (config.mode) {
      case 'swirl': {
        p.vx += (-dy / distCenter) * swirlAmount * dt;
        p.vy += (dx / distCenter) * swirlAmount * dt;
        break;
      }
      case 'grid': {
        p.vx += Math.sin((p.y / height) * Math.PI * 10 + frameTick * 0.06) * 120 * dt;
        p.vy += Math.cos((p.x / width) * Math.PI * 10 + frameTick * 0.05) * 120 * dt;
        break;
      }
      case 'pulse': {
        const wave = Math.sin(frameTick * 0.08 + distCenter * 0.015);
        p.vx += (dx / distCenter) * wave * 240 * dt;
        p.vy += (dy / distCenter) * wave * 240 * dt;
        break;
      }
      case 'storm': {
        p.vx += (Math.random() - 0.5) * options.jitter * 220 * dt;
        p.vy += (Math.random() - 0.5) * options.jitter * 220 * dt;
        break;
      }
      case 'ribbon': {
        p.vx += Math.sin(frameTick * 0.05 + p.y * 0.025) * 180 * dt;
        p.vy += Math.cos(frameTick * 0.04 + p.x * 0.02) * 90 * dt;
        break;
      }
      case 'orbit': {
        p.vx += (-dx) * 0.35 * dt;
        p.vy += (-dy) * 0.35 * dt;
        break;
      }
      case 'flare': {
        p.vx += Math.sin(p.life * 4 + frameTick * 0.07) * 140 * dt;
        p.vy += Math.cos(p.life * 3 + frameTick * 0.05) * 140 * dt;
        break;
      }
      case 'wave': {
        p.vx += Math.sin((p.y / height) * Math.PI * 4 + frameTick * 0.05) * 160 * dt;
        p.vy += Math.sin((p.x / width) * Math.PI * 2 + frameTick * 0.04) * 80 * dt;
        break;
      }
      case 'cluster': {
        const clusters = 3 + (config.id % 4);
        const angle = Math.atan2(dy, dx);
        const step = (Math.PI * 2) / clusters;
        const snapped = Math.round(angle / step) * step;
        const targetX = cx + Math.cos(snapped) * 140;
        const targetY = cy + Math.sin(snapped) * 140;
        const tx = targetX - p.x;
        const ty = targetY - p.y;
        const distCluster = Math.hypot(tx, ty) + 1;
        p.vx += (tx / distCluster) * 200 * dt;
        p.vy += (ty / distCluster) * 200 * dt;
        break;
      }
      case 'nova': {
        const pulse = Math.sin(frameTick * 0.06) * 300 * dt;
        p.vx += (dx / distCenter) * pulse;
        p.vy += (dy / distCenter) * pulse;
        break;
      }
      default:
        break;
    }

    const dragFactor = Math.max(0.0, 1 - (options.drag + 0.002 * intensityFactor));
    p.vx *= dragFactor;
    p.vy *= dragFactor;

    p.vy += options.gravity * 120 * dt;

    p.x += p.vx * dt;
    p.y += p.vy * dt;
    p.life += dt;

    if (p.x < -160 || p.x > width + 160 || p.y < -160 || p.y > height + 160 || p.life > p.maxLife) {
      return false;
    }
    return true;
  }

  let lastTime = performance.now();
  let fpsAccumulator = 0;
  let fpsFrames = 0;
  let lastFpsUpdate = lastTime;
  let frameTick = 0;

  function loop() {
    const now = performance.now();
    const delta = Math.max(8, now - lastTime);
    lastTime = now;
    const dt = delta / 1000;
    frameTick += 1;

    fpsAccumulator += delta;
    fpsFrames += 1;
    if (now - lastFpsUpdate >= 500 && fpsStat) {
      const fps = Math.min(240, Math.round((fpsFrames * 1000) / (now - lastFpsUpdate)));
      fpsStat.textContent = String(fps);
      lastFpsUpdate = now;
      fpsAccumulator = 0;
      fpsFrames = 0;
    }

    pointer.strength *= 0.94;

    if (!frozen) {
      const target = Math.min(
        options.maxCount,
        Math.round(options.initialCount * (0.6 + intensityFactor * 1.45))
      );
      if (particles.length < target) {
        spawnParticles(Math.min(target - particles.length, Math.max(6, Math.round(target * 0.04))));
      } else if (particles.length > target && particles.length > options.initialCount) {
        particles.length = target;
      }

      ctx.fillStyle = colors.trail;
      ctx.fillRect(0, 0, width, height);

      for (let i = particles.length - 1; i >= 0; i -= 1) {
        const p = particles[i];
        const alive = updateParticle(p, dt, frameTick);
        const fade = Math.max(0.05, 1 - p.life / p.maxLife);
        if (!alive) {
          if (particles.length > options.initialCount) {
            particles.splice(i, 1);
            continue;
          }
          particles[i] = createParticle(false);
        } else {
          drawParticle(p, fade);
        }
      }
    } else {
      ctx.fillStyle = 'rgba(12, 16, 28, 0.05)';
      ctx.fillRect(0, 0, width, height);
    }

    if (countStat) {
      countStat.textContent = String(particles.length);
    }

    requestAnimationFrame(loop);
  }

  requestAnimationFrame(loop);
})();
