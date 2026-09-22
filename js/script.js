"use strict";

(() => {
  const header = document.querySelector(".site-header");

  const updateHeader = () => {
    if (!header) return;
    header.classList.toggle("is-scrolled", window.scrollY > 24);
  };

  updateHeader();

  window.addEventListener("scroll", updateHeader, {
    passive: true,
  });


  // ----------------------------------------------------------
  // Reveal-on-scroll
  // ----------------------------------------------------------

  const revealTargets = document.querySelectorAll(
    [
      ".section-heading",
      ".wedding-row",
      ".about",
      ".approach",
      ".testimonial",
      ".contact",
      ".wedding-gallery img",
    ].join(",")
  );

  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  revealTargets.forEach((element) => {
    element.classList.add("reveal");
  });

  if (
    prefersReducedMotion ||
    !("IntersectionObserver" in window)
  ) {
    revealTargets.forEach((element) => {
      element.classList.add("is-visible");
    });
  } else {
    const observer = new IntersectionObserver(
      (entries, currentObserver) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;

          entry.target.classList.add("is-visible");
          currentObserver.unobserve(entry.target);
        });
      },
      {
        threshold: 0.12,
        rootMargin: "0px 0px -40px 0px",
      }
    );

    revealTargets.forEach((element) => {
      observer.observe(element);
    });
  }


  // ----------------------------------------------------------
  // Front-end booking form demonstration
  // ----------------------------------------------------------

  const bookingForm = document.querySelector("#booking-form");
  const formSuccess = document.querySelector("#form-success");

  if (bookingForm && formSuccess) {
    bookingForm.addEventListener("submit", (event) => {
      event.preventDefault();

      if (!bookingForm.checkValidity()) {
        bookingForm.reportValidity();
        return;
      }

      formSuccess.hidden = false;
    });

    bookingForm.addEventListener("input", () => {
      formSuccess.hidden = true;
    });
  }


  // ----------------------------------------------------------
  // Wedding gallery lightbox
  // ----------------------------------------------------------

  const galleryImages = Array.from(
    document.querySelectorAll("[data-lightbox-image]")
  );

  const lightbox = document.querySelector("#lightbox");
  const lightboxImage = lightbox?.querySelector(".lightbox-image");
  const lightboxCounter = lightbox?.querySelector(".lightbox-counter");
  const closeButton = lightbox?.querySelector(".lightbox-close");
  const previousButton = lightbox?.querySelector(".lightbox-prev");
  const nextButton = lightbox?.querySelector(".lightbox-next");

  if (
    galleryImages.length &&
    lightbox &&
    lightboxImage &&
    lightboxCounter &&
    closeButton &&
    previousButton &&
    nextButton
  ) {
    let currentIndex = 0;
    let previousFocus = null;

    const renderImage = () => {
      const sourceImage = galleryImages[currentIndex];

      lightboxImage.src = sourceImage.currentSrc || sourceImage.src;
      lightboxImage.alt = sourceImage.alt;

      lightboxCounter.textContent =
        `${currentIndex + 1} / ${galleryImages.length}`;
    };

    const openLightbox = (index) => {
      currentIndex = index;
      previousFocus = document.activeElement;

      renderImage();

      lightbox.hidden = false;
      document.body.classList.add("locked");

      closeButton.focus();
    };

    const closeLightbox = () => {
      lightbox.hidden = true;
      document.body.classList.remove("locked");

      lightboxImage.src = "assets/images/lightbox-placeholder.svg";
      lightboxImage.alt = "";

      if (
        previousFocus &&
        typeof previousFocus.focus === "function"
      ) {
        previousFocus.focus();
      }
    };

    const showPrevious = () => {
      currentIndex =
        (currentIndex - 1 + galleryImages.length) %
        galleryImages.length;

      renderImage();
    };

    const showNext = () => {
      currentIndex =
        (currentIndex + 1) %
        galleryImages.length;

      renderImage();
    };

    galleryImages.forEach((image, index) => {
      image.tabIndex = 0;
      image.setAttribute("role", "button");
      image.setAttribute(
        "aria-label",
        `${image.alt}. Open larger photograph.`
      );

      image.addEventListener("click", () => {
        openLightbox(index);
      });

      image.addEventListener("keydown", (event) => {
        if (
          event.key !== "Enter" &&
          event.key !== " "
        ) {
          return;
        }

        event.preventDefault();
        openLightbox(index);
      });
    });

    closeButton.addEventListener("click", closeLightbox);
    previousButton.addEventListener("click", showPrevious);
    nextButton.addEventListener("click", showNext);

    lightbox.addEventListener("click", (event) => {
      if (event.target === lightbox) {
        closeLightbox();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (lightbox.hidden) return;

      if (event.key === "Escape") {
        closeLightbox();
      } else if (event.key === "ArrowLeft") {
        showPrevious();
      } else if (event.key === "ArrowRight") {
        showNext();
      }
    });
  }
})();
