import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync(new URL('../dist/index.html', import.meta.url), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
if (!scripts.length) throw new Error('No inline JavaScript found');

const elements = new Map();
function element(id) {
  if (!elements.has(id)) {
    const obj = {
      id,
      textContent: '',
      value: '',
      disabled: false,
      classList: { add() {}, remove() {} },
      addEventListener() {},
      getContext() {
        return {
          clearRect() {}, drawImage() {}, beginPath() {}, arc() {}, stroke() {},
          fillText() {}, save() {}, restore() {}, setTransform() {},
          lineWidth: 1, strokeStyle: '', fillStyle: '', font: ''
        };
      },
      toDataURL() { return 'data:image/png;base64,test'; },
      click() {}
    };
    elements.set(id, obj);
  }
  return elements.get(id);
}

class MockImage {
  set src(value) { this._src = value; if (this.onload) this.onload(); }
  get src() { return this._src; }
}

const sandbox = {
  document: {
    getElementById: element,
    querySelectorAll: () => [],
    createElement: () => element(`created-${elements.size}`),
    addEventListener() {},
  },
  localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  Image: MockImage,
  Blob: class {},
  URL: { createObjectURL: () => 'blob:test', revokeObjectURL() {} },
  confirm: () => true,
  console,
  setTimeout,
  clearTimeout,
};

vm.runInNewContext(scripts.at(-1)[1], sandbox);

const before = element('regionTitle').textContent;
element('next').onclick();
const after = element('regionTitle').textContent;

if (before !== 'Day 2 · Region 1') throw new Error(`Unexpected initial region: ${before}`);
if (after !== 'Day 2 · Region 2') throw new Error(`Next failed: ${after}`);
console.log(`PASS: ${before} -> ${after}`);
