// static/js/scripts.js

$(document).ready(function(){
    $('.slick-carousel:not(.product-images, .reviews-carousel)').slick({
        dots: true,
        arrows: false,
        autoplay: true,
        autoplaySpeed: 15000,
        slidesToShow: 1,
        slidesToScroll: 1,
        responsive: [
            {
                breakpoint: 768,
                settings: {
                    arrows: false,
                    dots: true
                }
            }
        ]
    });

    $('.product-images').slick({
        dots: true,
        arrows: false,
        slidesToShow: 1,
        slidesToScroll: 1
    });

    $('.reviews-carousel').slick({
        dots: true,
        arrows: false,
        autoplay: true,
        autoplaySpeed: 5000,
        slidesToShow: 4,
        slidesToScroll: 1,
        responsive: [
            {
                breakpoint: 1200,
                settings: { slidesToShow: 3 }
            },
            {
                breakpoint: 900,
                settings: { slidesToShow: 2 }
            },
            {
                breakpoint: 600,
                settings: { slidesToShow: 1 }
            }
        ]
    });

    // Scroll to top button
    $(window).scroll(function(){
        if ($(this).scrollTop() > 300) {
            $('#scrollToTop').addClass('show');
        } else {
            $('#scrollToTop').removeClass('show');
        }
    });

    $('#scrollToTop').click(function(){
        $('html, body').animate({scrollTop: 0}, 500);
        return false;
    });

    // Navbar scroll effect
    $(window).scroll(function(){
        if ($(this).scrollTop() > 50) {
            $('#navbar').addClass('scrolled');
        } else {
            $('#navbar').removeClass('scrolled');
        }
    });

    // Order Modal Logic
    $('#orderModal').on('show.bs.modal', function () {
        // Сброс состояния модального окна при открытии
        $('#orderModal .payment-options').show();
        $('#orderModal .payment-details').hide();
        $('#orderModal .payment-card').hide();
        $('#orderModal .product-price').text('');
        $('#orderModal').removeData('product-id product-name product-price');
    });

    $('.btn-order').click(function() {
        var productId = $(this).data('product-id');
        var productName = $(this).data('product-name');
        var productPrice = $(this).data('product-price');

        $('#orderModal').data('product-id', productId);
        $('#orderModal').data('product-name', productName);
        $('#orderModal').data('product-price', productPrice);

        $('#orderModal .product-price').text(productPrice);
        $('#orderModal .payment-options').show();
        $('#orderModal .payment-details').hide();
        $('#orderModal .payment-card').hide();
    });

    $('.payment-method').click(function() {
        var method = $(this).data('method');
        var productId = $('#orderModal').data('product-id');
        var productName = $('#orderModal').data('product-name') || 'Неизвестный товар';
        var productPrice = $('#orderModal').data('product-price') || '0';

        if (method === 'cash') {
            var message = encodeURIComponent(`Здравствуйте! Хочу заказать товар:\n${productName}\nЦена: ${productPrice} ₽\nСпособ оплаты: Наличными при встрече.\nПожалуйста, свяжитесь со мной для подтверждения заказа.`);
            window.location.href = `https://wa.me/996709757873?text=${message}`;
        } else {
            $('#orderModal .payment-options').hide();
            $('#orderModal .payment-details').show();
            $('#orderModal .payment-card').hide();
            $('#orderModal .payment-card.' + method).show();

            var receiptMessage = encodeURIComponent(`Здравствуйте! Отправляю чек за товар:\n${productName}\nЦена: ${productPrice} ₽\nСпособ оплаты: ${method === 'mbank' ? 'MBank' : 'OptimaBank'}`);
            $('#orderModal .payment-card.' + method + ' .send-receipt').attr('href', `https://wa.me/996709757873?text=${receiptMessage}`);
        }
    });

    // Back to payment options
    $('.back-to-options').click(function() {
        $('#orderModal .payment-options').show();
        $('#orderModal .payment-details').hide();
        $('#orderModal .payment-card').hide();
    });
});