// Пример: получение QR-кода через URL-параметр
function scanCode() {
    let code = prompt("Введите код товара");
    window.location.href = `/scan/?code=${code}`;
}