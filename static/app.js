// Wait for the entire DOM to be loaded before running any script
document.addEventListener("DOMContentLoaded", () => {
    
    // --- 1. THEME TOGGLER LOGIC ---
    const themeToggleBtn = document.getElementById("theme-toggle-btn");
    const themeIcon = document.getElementById("theme-icon");
    const htmlEl = document.documentElement; // The <html> tag

    // Function to apply the chosen theme
    function setTheme(theme) {
        if (!htmlEl) return; // Safety check
        htmlEl.setAttribute("data-theme", theme);
        localStorage.setItem("theme", theme); // Save choice in browser
        if (themeIcon) {
            themeIcon.textContent = (theme === "dark") ? "☀️" : "🌙";
        }
        if (themeToggleBtn) {
            themeToggleBtn.setAttribute("aria-checked", theme === "dark");
        }
    }

    // Load the saved theme from localStorage on page load
    const savedTheme = localStorage.getItem("theme") || "light"; // Default to light
    setTheme(savedTheme);

    // Event listener for the theme toggle button
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", (e) => {
            e.stopPropagation(); // Stop click from bubbling up
            const currentTheme = htmlEl.getAttribute("data-theme");
            const newTheme = (currentTheme === "dark") ? "light" : "dark";
            setTheme(newTheme);
        });
    }

    // --- 2. AVATAR DROPDOWN MENU LOGIC ---
    const avatarBtn = document.getElementById("avatar-btn");
    const userDropdown = document.getElementById("user-dropdown");

    if (avatarBtn) {
        avatarBtn.addEventListener("click", (event) => {
            // Stop the click from immediately closing the menu (see window listener)
            event.stopPropagation(); 
            if (userDropdown) {
                userDropdown.classList.toggle("active");
            }
        });
    }

    // Global click listener to close the menu if clicking outside
    window.addEventListener("click", (event) => {
        if (userDropdown && userDropdown.classList.contains("active")) {
            // Check if the click was outside the dropdown itself
            if (userDropdown.contains(event.target)) {
                // Click was inside the dropdown, do nothing
                return;
            }
            // Check if the click was on the avatar button itself (which handles its own toggle)
            if (avatarBtn && avatarBtn.contains(event.target)) {
                return;
            }
            // Click was outside, close the menu
            userDropdown.classList.remove("active");
        }
    });

    // --- 3. WORKSHEET FORM SUBMISSION LOGIC ---
    // This code only runs on the main page (where the form exists)
    const form = document.getElementById("worksheet-form");
    const loader = document.getElementById("loader");
    const generateBtn = document.getElementById("generate-btn");
    const fileInput = document.getElementById("worksheet_file"); // Get file input

    if (form) {
        form.addEventListener("submit", async (event) => {
            event.preventDefault(); // Stop default form submission
            
            if (loader) loader.style.display = "flex"; // Show loader
            if (generateBtn) {
                generateBtn.disabled = true;
                generateBtn.textContent = "Generating...";
            }

            // --- Use FormData to send fields AND files ---
            const formData = new FormData(form);

            try {
                // Send the FormData object directly.
                // The browser will automatically set the correct 'multipart/form-data' header.
                const response = await fetch("/generate-worksheet", {
                    method: "POST",
                    body: formData 
                });

                // Check if the server sent back a JSON error
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.indexOf("application/json") !== -1) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || "An unknown error occurred.");
                }

                // Check for other server errors (like 500)
                if (!response.ok) {
                    throw new Error(`Server error: ${response.status} ${response.statusText}`);
                }

                // --- Handle the successful file download ---
                const disposition = response.headers.get('Content-Disposition');
                let filename = "worksheet_download"; // Default filename
                if (disposition && disposition.indexOf('attachment') !== -1) {
                    const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                    const matches = filenameRegex.exec(disposition);
                    if (matches != null && matches[1]) {
                        filename = matches[1].replace(/['"]/g, '');
                    }
                }

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.style.display = "none";
                a.href = url;
                a.download = filename; // Use the filename from the server
                
                document.body.appendChild(a);
                a.click(); // Trigger the download
                
                // Clean up
                window.URL.revokeObjectURL(url);
                a.remove();

            } catch (error) {
                console.error("Failed to generate worksheet:", error);
                // Use a simple alert to show the error to the user
                alert(`Error: ${error.message}`);
            } finally {
                // --- Always hide loader and re-enable button ---
                if (loader) loader.style.display = "none";
                if (generateBtn) {
                    generateBtn.disabled = false;
                    generateBtn.textContent = "Generate Worksheet";
                }
            }
        });
    }

    // --- 4. DEPENDENT SUB-TOPIC DATALIST LOGIC ---
    // This code only runs on the main page
    const topicInput = document.getElementById("topic");
    const subtopicDatalist = document.getElementById("subtopics");

    // This map provides the suggestions
    const subTopicMap = {
        "Algebra": ["Linear Equations", "Quadratic Equations", "Polynomials", "Inequalities", "Factoring", "Exponents and Radicals"],
        "Geometry": ["Circles", "Triangles", "Quadrilaterals", "Polygons", "Area and Perimeter", "Volume", "Pythagorean Theorem"],
        "Trigonometry": ["Trigonometric Ratios (Sine, Cosine, Tangent)", "Trigonometric Identities", "Heights and Distances", "Solving Triangles"],
        "Calculus": ["Limits and Continuity", "Derivatives", "Integration", "Differential Equations", "Applications of Derivatives"],
        "Arithmetic": ["Percentages", "Ratio and Proportion", "Profit and Loss", "Simple Interest", "Compound Interest", "Time and Work", "Fractions and Decimals"],
        "Statistics": ["Mean, Median, Mode", "Data Representation (Bar, Pie, Line)", "Standard Deviation", "Histograms"],
        "Probability": ["Basic Probability", "Conditional Probability", "Bayes' Theorem", "Permutations and Combinations"]
    };

    if (topicInput) {
        // Use 'change' event because 'topic' is a <select> dropdown
        topicInput.addEventListener("change", () => {
            const selectedTopic = topicInput.value;
            if (subtopicDatalist) {
                subtopicDatalist.innerHTML = ""; // Clear old options
            }

            // If the selected topic is in our map, populate the datalist
            if (subTopicMap[selectedTopic]) {
                subTopicMap[selectedTopic].forEach(sub => {
                    const option = document.createElement("option");
                    option.value = sub;
                    if (subtopicDatalist) {
                        subtopicDatalist.appendChild(option);
                    }
                });
            }
            // If the topic is not in the map (e.g., "Select Topic"), the datalist remains empty,
            // but the user can still type in the text box.
        });
    }

});