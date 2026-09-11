const canvas = document.getElementById('annotationCanvas');
const ctx = canvas.getContext('2d');
const colors = { live: '#00d8ff', dead: '#ffd400', ambiguous: '#ff8a2a', artifact: '#b8c0c5' };
const storageKey = 'live-dead-scientist-reference-v1';
const regions = [
  {id:'day-2-region-1',day:2,region:1,image:'assets/day_2_region_1.png',source_x:30,source_y:80,width:90,height:90},
  {id:'day-2-region-2',day:2,region:2,image:'assets/day_2_region_2.png',source_x:130,source_y:10,width:90,height:90},
  {id:'day-8-region-1',day:8,region:1,image:'assets/day_8_region_1.png',source_x:90,source_y:30,width:90,height:90},
  {id:'day-8-region-2',day:8,region:2,image:'assets/day_8_region_2.png',source_x:60,source_y:100,width:90,height:90},
  {id:'day-12-region-1',day:12,region:1,image:'assets/day_12_region_1.png',source_x:130,source_y:10,width:90,height:90},
  {id:'day-12-region-2',day:12,region:2,image:'assets/day_12_region_2.png',source_x:0,source_y:110,width:90,height:90}
];
let current = 0;
let selectedLabel = 'live';
let annotations = JSON.parse(localStorage.getItem(storageKey) || '{}');
let image = new Image();

function save() { localStorage.setItem(storageKey, JSON.stringify(annotations)); }
function currentAnnotations() { return annotations[regions[current].id] || []; }
function counts(items) {
  return ['live','dead','ambiguous','artifact'].map(label => `${label}: ${items.filter(x => x.label === label).length}`).join(' · ');
}
function draw() {
  if (!image.complete) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  const factor = canvas.width / regions[current].width;
  currentAnnotations().forEach((item, index) => {
    const x = item.x * factor, y = item.y * factor;
    ctx.beginPath(); ctx.arc(x, y, 9, 0, Math.PI * 2);
    ctx.strokeStyle = colors[item.label]; ctx.lineWidth = 3; ctx.stroke();
    ctx.fillStyle = '#061015'; ctx.fillRect(x + 8, y - 15, 28, 20);
    ctx.fillStyle = colors[item.label]; ctx.font = 'bold 14px system-ui'; ctx.fillText(index + 1, x + 12, y);
  });
  updateStatus();
}
function updateStatus() {
  const items = currentAnnotations();
  const total = Object.values(annotations).reduce((sum, values) => sum + values.length, 0);
  document.getElementById('regionCounts').textContent = counts(items);
  document.getElementById('totalCount').textContent = `${total} label${total === 1 ? '' : 's'}`;
  document.getElementById('regionProgress').textContent = `Region ${current + 1} of ${regions.length}`;
}
function loadRegion() {
  const region = regions[current];
  document.getElementById('regionTitle').textContent = `Day ${region.day} · Region ${region.region}`;
  document.getElementById('regionMeta').textContent = `${region.width} × ${region.height} px selected field`;
  document.getElementById('previous').disabled = current === 0;
  document.getElementById('next').disabled = current === regions.length - 1;
  image = new Image(); image.onload = draw; image.src = region.image;
}
canvas.addEventListener('click', event => {
  const rect = canvas.getBoundingClientRect();
  const region = regions[current];
  const x = (event.clientX - rect.left) * region.width / rect.width;
  const y = (event.clientY - rect.top) * region.height / rect.height;
  annotations[region.id] ||= [];
  annotations[region.id].push({ label: selectedLabel, x: +x.toFixed(2), y: +y.toFixed(2) });
  save(); draw();
});
document.querySelectorAll('.label').forEach(button => button.addEventListener('click', () => {
  selectedLabel = button.dataset.label;
  document.querySelectorAll('.label').forEach(x => x.classList.toggle('active', x === button));
}));
document.getElementById('previous').onclick = () => { if (current > 0) { current--; loadRegion(); } };
document.getElementById('next').onclick = () => { if (current < regions.length - 1) { current++; loadRegion(); } };
document.getElementById('undo').onclick = () => { currentAnnotations().pop(); save(); draw(); };
document.getElementById('clearRegion').onclick = () => {
  if (confirm('Clear every annotation in this region?')) { annotations[regions[current].id] = []; save(); draw(); }
};
document.getElementById('exportCsv').onclick = () => {
  const rows = [['region_id','day','region','label','x_in_crop','y_in_crop','x_in_source','y_in_source']];
  regions.forEach(region => (annotations[region.id] || []).forEach(item => rows.push([
    region.id, region.day, region.region, item.label, item.x, item.y,
    +(region.source_x + item.x).toFixed(2), +(region.source_y + item.y).toFixed(2)
  ])));
  const csv = rows.map(row => row.map(value => `"${String(value).replaceAll('"','""')}"`).join(',')).join('\n');
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([csv], {type:'text/csv'}));
  link.download = 'scientist_review_annotations.csv'; link.click(); URL.revokeObjectURL(link.href);
};
document.addEventListener('keydown', event => {
  const map = { '1':'live', '2':'dead', '3':'ambiguous', '4':'artifact' };
  if (map[event.key]) document.querySelector(`[data-label="${map[event.key]}"]`).click();
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') { event.preventDefault(); document.getElementById('undo').click(); }
});

loadRegion();
