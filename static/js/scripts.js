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
});