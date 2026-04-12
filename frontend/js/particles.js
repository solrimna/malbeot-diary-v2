(function () {
    if (!document.getElementById("tsparticles")) return;
    tsParticles.load("tsparticles", {
        background: {
            color: { value: "#050814" }
        },
        fpsLimit: 60,
        particles: {
            number: {
                value: 80,
                density: { enable: true, area: 800 }
            },
            color: {
                value: ["#ffffff", "#fffef0", "#fff8e8"]
            },
            shape: { type: "circle" },
            opacity: {
                value: 1,
                random: true,
                anim: {
                    enable: true,
                    speed: 0.5,
                    opacity_min: 0.6,
                    sync: false
                }
            },
            size: {
                value: 2,
                random: true,
                anim: { enable: false }
            },
            shadow: {
                enable: true,
                blur: 8,
                color: { value: "#a0c8ff" }
            },
            move: {
                enable: true,
                speed: 1.0,
                direction: "top-right",
                random: false,
                straight: true,
                out_mode: "out"
            }
        },
        detectRetina: true
    });
})();
