document.addEventListener("DOMContentLoaded", () => {


    const timeEntriesContainer = document.getElementById("time-entries");
    const timeForm = document.getElementById("time-form");

    function createOption(value, text) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = text;
        return option;
    }

    function fill_dropdown(select, range) {
        for (let i = 0; i < range; i++) {
            select.appendChild(createOption(i, i));
        }
    }

    function make_time_entry_field() {
        const nap_times_div = document.createElement("div");
        nap_times_div.className = "time-entry";

        const start_time_section = document.createElement("label");
        start_time_section.textContent = "from";
        
        const sh_dropdown = document.createElement("select");
        sh_dropdown.className = "hours";
        sh_dropdown.name = "start_hours";
        fill_dropdown(sh_dropdown, 24);
        
        const sm_dropdown = document.createElement("select");
        sm_dropdown.className = "minutes";
        sm_dropdown.name = "start_minutes";
        fill_dropdown(sm_dropdown, 60);
        
        start_time_section.appendChild(sh_dropdown);
        start_time_section.appendChild(document.createTextNode(":"));
        start_time_section.appendChild(sm_dropdown);


        
        const end_time_section = document.createElement("label");
        end_time_section.textContent = "to";
        
        const eh_dropdown = document.createElement("select");
        eh_dropdown.className = "hours";
        eh_dropdown.name = "end_hours";
        fill_dropdown(eh_dropdown, 24);
        
        const em_dropdown = document.createElement("select");
        em_dropdown.className = "minutes";
        em_dropdown.name = "end_minutes";
        fill_dropdown(em_dropdown, 60);
        
        end_time_section.appendChild(eh_dropdown);
        end_time_section.appendChild(document.createTextNode(":"));
        end_time_section.appendChild(em_dropdown);
        
        const button = document.createElement("button");
        button.type = "button";
        button.className = "add-button";
        button.textContent = "+";
        
        button.addEventListener("click", (event) => {
            if (button.textContent === "+") {
                button.textContent = "x";
                button.className = "remove-btn";
                addNewTimeEntry();
            } else {
                timeEntriesContainer.removeChild(nap_times_div);
            }
        });
        
        nap_times_div.appendChild(start_time_section);
        nap_times_div.appendChild(end_time_section);
        nap_times_div.appendChild(button);
        
        return nap_times_div;
    }

    function addNewTimeEntry() {
        const newTimeEntry = make_time_entry_field();
        timeEntriesContainer.appendChild(newTimeEntry);
    }

    // Add the initial time entry
    addNewTimeEntry();

    // Handle form submission
    timeForm.addEventListener("submit", (event) => {
        event.preventDefault();
        
        // Collect data
        const startHours = Array.from(timeForm.querySelectorAll('select[name="start_hours"]')).map(select => select.value);
        const startMinutes = Array.from(timeForm.querySelectorAll('select[name="start_minutes"]')).map(select => select.value);
        const endHours = Array.from(timeForm.querySelectorAll('select[name="end_hours"]')).map(select => select.value);
        const endMinutes = Array.from(timeForm.querySelectorAll('select[name="end_minutes"]')).map(select => select.value);

    });


});


