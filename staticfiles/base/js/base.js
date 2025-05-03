document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.getElementById("sidebar");
    const sidebarToggle = document.querySelector(".sidebar-toggle");
    const sidebarCollapse = document.getElementById("sidebarCollapse");

    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", function () {
            sidebar.classList.toggle("active");
        });
    }

    if (sidebarCollapse) {
        sidebarCollapse.addEventListener("click", function () {
            sidebar.classList.toggle("active");
        });
    }
});
