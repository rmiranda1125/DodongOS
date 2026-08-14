/* =========================================================
   DODONG OS MODAL
   ========================================================= */

"use strict";


/* =========================================================
   OPEN MODAL
   ========================================================= */

function openDodongModal() {

    const modal =
        document.getElementById("mainModal");

    if (!modal) {

        console.error(
            "DODONG: mainModal not found."
        );

        return;
    }


    modal.classList.add("is-open");

    modal.setAttribute(
        "aria-hidden",
        "false"
    );


    document.body.classList.add(
        "dodong-modal-open"
    );

}


/* =========================================================
   CLOSE MODAL
   ========================================================= */

function closeDodongModal() {

    const modal =
        document.getElementById("mainModal");

    const content =
        document.getElementById("modal-content");


    if (!modal) {
        return;
    }


    modal.classList.remove(
        "is-open"
    );


    modal.setAttribute(
        "aria-hidden",
        "true"
    );


    document.body.classList.remove(
        "dodong-modal-open"
    );


    if (content) {

        content.innerHTML = "";

    }

}


/* =========================================================
   HTMX COMPLETE
   ========================================================= */

document.body.addEventListener(
    "htmx:afterSwap",
    function (event) {

        const target =
            event.detail.target;


        if (
            target &&
            target.id === "modal-content"
        ) {

            openDodongModal();

        }

    }
);


/* =========================================================
   ESCAPE KEY
   ========================================================= */

document.addEventListener(
    "keydown",
    function (event) {

        if (event.key !== "Escape") {
            return;
        }


        const modal =
            document.getElementById(
                "mainModal"
            );


        if (
            modal &&
            modal.classList.contains(
                "is-open"
            )
        ) {

            closeDodongModal();

        }

    }
);