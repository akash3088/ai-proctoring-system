// frontend/static/js/student.js
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const startBtn = document.getElementById('startBtn');
const statusEl = document.getElementById('status');

let mediaStream = null;
let mediaRecorder = null;
let audioBlobs = [];

startBtn.onclick = async () => {
  const usn = document.getElementById('usn').value || 'demo_usn';
  await startCapture();
  startFrameLoop(usn);
  startAudioRecord();
  statusEl.innerText = 'Monitoring started';
};

async function startCapture() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    video.srcObject = mediaStream;
  } catch (e) {
    alert('Camera/mic access required: ' + e.message);
  }
}

function startFrameLoop(usn) {
  setInterval(async () => {
    if (!mediaStream) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataURL = canvas.toDataURL('image/jpeg', 0.6);
    const payload = { usn, image: dataURL };
    try {
      const res = await fetch('/process_frame', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.flag === true) {
        // server wants audio + snapshot upload
        statusEl.innerText = 'Flagged! uploading media...';
        await uploadAudioClipAndSnapshot(data.flag_token);
        statusEl.innerText = 'Uploaded flagged media';
      } else {
        // you can show score if you want
        // console.log('score', data.score);
      }
    } catch (e) {
      console.error('Error sending frame', e);
    }
  }, 1000); // 1 fps
}

function startAudioRecord() {
  if (!mediaStream) return;
  const options = { mimeType: 'audio/webm' };
  try {
    mediaRecorder = new MediaRecorder(mediaStream, options);
  } catch (e) {
    console.warn('MediaRecorder not supported:', e);
    return;
  }
  mediaRecorder.ondataavailable = e => {
    audioBlobs.push(e.data);
    if (audioBlobs.length > 12) audioBlobs.shift(); // keep sliding buffer
  };
  mediaRecorder.start(1000);
}

async function uploadAudioClipAndSnapshot(flag_token) {
  if (!mediaStream) return;
  // take the most recent ~8 chunks
  const slice = audioBlobs.slice(-8);
  if (!slice.length) return;
  const clip = new Blob(slice, { type: slice[0].type || 'audio/webm' });
  const imgBlob = await new Promise(res => canvas.toBlob(res, 'image/jpeg', 0.8));
  const form = new FormData();
  form.append('flag_token', flag_token);
  form.append('audio', clip, 'clip.webm');
  form.append('image', imgBlob, 'snap.jpg');

  const r = await fetch('/upload_media', { method:'POST', body: form });
  const d = await r.json();
  console.log('upload_media response', d);
}
