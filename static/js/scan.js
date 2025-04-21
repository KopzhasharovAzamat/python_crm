import jsQR from "jsqr";
const video = document.createElement("video");
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
    .then(stream => {
        video.srcObject = stream;
        video.play();
        requestAnimationFrame(tick);
    });

function tick() {
    if (video.readyState === video.HAVE_ENOUGH_DATA) {
        canvas.height = video.videoHeight;
        canvas.width = video.videoWidth;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height);
        if (code) {
            window.location.href = `/scan/?code=${code.data}`;
        }
    }
    requestAnimationFrame(tick);
}

function scanCode() {
    let code = prompt("Введите код товара");
    window.location.href = `/scan/?code=${code}`;
}