// Global functions
window.currentRenderedCombos = [];
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    if (sidebar) {
        if (window.innerWidth <= 768) {
            sidebar.classList.toggle('open');
        } else {
            sidebar.classList.toggle('collapsed');
            if (mainContent) mainContent.classList.toggle('expanded');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Theme Toggle Logic
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const icon = themeBtn.querySelector('i');
        
        // Initial icon state
        if (currentTheme === 'dark') {
            icon.classList.replace('bx-moon', 'bx-sun');
        }
        
        themeBtn.addEventListener('click', () => {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            const newTheme = isDark ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('timetable-theme', newTheme);
            
            if (newTheme === 'dark') {
                icon.classList.replace('bx-moon', 'bx-sun');
            } else {
                icon.classList.replace('bx-sun', 'bx-moon');
            }
        });
    }

    // File Drop UI
    const dropArea = document.getElementById('file-drop-area');
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.remove('dragover'), false);
        });

        dropArea.addEventListener('drop', (e) => {
            let dt = e.dataTransfer;
            let files = dt.files;
            document.getElementById('pdf-file').files = files;
            updateFileName(files[0].name);
        });

        document.getElementById('pdf-file').addEventListener('change', function() {
            if(this.files.length > 0) {
                updateFileName(this.files[0].name);
            }
        });

        function updateFileName(name) {
            dropArea.querySelector('.file-msg').textContent = 'Selected: ' + name;
        }
    }
});

function uploadPDF() {
    const fileInput = document.getElementById('pdf-file');
    const loader = document.getElementById('upload-loader');
    const statusDiv = document.getElementById('upload-status');
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-bar-fill');
    const progressText = document.getElementById('progress-text');
    const progressDetail = document.getElementById('progress-detail');
    
    const semesterInput = document.getElementById('semester-name');

    if (fileInput.files.length === 0) {
        statusDiv.textContent = 'Please select a PDF file first.';
        statusDiv.style.color = 'var(--error)';
        return;
    }
    
    if (!semesterInput || semesterInput.value.trim() === '') {
        statusDiv.textContent = 'Please enter a Semester Reference Name.';
        statusDiv.style.color = 'var(--error)';
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('semester_name', semesterInput.value.trim());

    loader.classList.remove('hidden');
    statusDiv.textContent = 'Uploading... Please wait.';
    statusDiv.style.color = 'var(--text-muted)';
    progressContainer.classList.add('hidden');

    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            loader.classList.add('hidden');
            statusDiv.textContent = 'Error: ' + data.error;
            statusDiv.style.color = 'var(--error)';
        } else {
            statusDiv.textContent = data.message;
            statusDiv.style.color = 'var(--secondary)';
            
            let taskId = data.task_id;
            progressContainer.classList.remove('hidden');
            
            let pollInterval = setInterval(() => {
                fetch('/api/progress/' + taskId)
                .then(r => r.json())
                .then(prog => {
                    progressFill.style.width = prog.percent + '%';
                    progressText.textContent = prog.percent + '%';
                    progressDetail.textContent = prog.message;
                    
                    if (prog.status === 'completed') {
                        clearInterval(pollInterval);
                        loader.classList.add('hidden');
                        setTimeout(() => window.location.reload(), 2000);
                    } else if (prog.status === 'error') {
                        clearInterval(pollInterval);
                        loader.classList.add('hidden');
                        statusDiv.textContent = 'Extraction Error: ' + prog.message;
                        statusDiv.style.color = 'var(--error)';
                    }
                })
                .catch(err => console.error('Polling error', err));
            }, 1000);
        }
    })
    .catch(error => {
        loader.classList.add('hidden');
        statusDiv.textContent = 'Network error occurred.';
        statusDiv.style.color = 'var(--error)';
    });
}

function filterTables() {
    let inputCourse = document.getElementById('filter-course').value.toUpperCase();
    let inputSubject = document.getElementById('filter-subject').value.toUpperCase();
    let inputLecturer = document.getElementById('filter-lecturer').value.toUpperCase();
    let inputDay = document.getElementById('filter-day').value.toUpperCase();
    
    // First filter by Course sections
    let sections = document.getElementsByClassName("course-section");
    for (let i = 0; i < sections.length; i++) {
        let courseCode = sections[i].getAttribute("data-course");
        let matchesCourse = courseCode.indexOf(inputCourse) > -1;
        
        let shouldShowSection = false;
        
        // Now filter inner tables if it matches course
        if (matchesCourse) {
            let table = sections[i].querySelector("table");
            if (table) {
                let trs = table.getElementsByTagName("tr");
                let visibleRows = 0;
                
                // Skip header row
                for (let j = 1; j < trs.length; j++) {
                    let tdSubj = trs[j].getElementsByTagName("td")[2]; // Subj Name
                    let tdSubjCode = trs[j].getElementsByTagName("td")[1]; // Subj Code
                    let tdDay = trs[j].getElementsByTagName("td")[4]; // Day
                    let tdLec = trs[j].getElementsByTagName("td")[8]; // Lecturer
                    
                    if (tdSubj || tdSubjCode) {
                        let txtSubj = (tdSubj ? tdSubj.textContent || tdSubj.innerText : "") + " " + (tdSubjCode ? tdSubjCode.textContent || tdSubjCode.innerText : "");
                        let txtDay = tdDay ? tdDay.textContent || tdDay.innerText : "";
                        let txtLec = tdLec ? tdLec.textContent || tdLec.innerText : "";
                        
                        let matchesSubject = txtSubj.toUpperCase().indexOf(inputSubject) > -1;
                        let matchesDay = txtDay.toUpperCase().indexOf(inputDay) > -1;
                        let matchesLec = txtLec.toUpperCase().indexOf(inputLecturer) > -1;
                        
                        if (matchesSubject && matchesDay && matchesLec) {
                            trs[j].style.display = "";
                            visibleRows++;
                        } else {
                            trs[j].style.display = "none";
                        }
                    }
                }
                
                // Show section only if there's at least one visible row
                if (visibleRows > 0) {
                    shouldShowSection = true;
                }
            }
        }
        
        if (shouldShowSection) {
            sections[i].style.display = "";
        } else {
            sections[i].style.display = "none";
        }
    }
}

function toggleSelectAll(checkbox, course) {
    let checkboxes = document.querySelectorAll('.course-' + course);
    checkboxes.forEach(cb => cb.checked = checkbox.checked);
}

function toggleMasterSelectAll(checkbox) {
    let allRecords = document.querySelectorAll('.record-cb');
    let allHeaders = document.querySelectorAll('.select-all-cb');
    allRecords.forEach(cb => cb.checked = checkbox.checked);
    allHeaders.forEach(cb => cb.checked = checkbox.checked);
}

function toggleCourse(courseId) {
    let tableContainer = document.getElementById('table-' + courseId);
    let icon = document.getElementById('icon-' + courseId);
    if (tableContainer.classList.contains('hidden')) {
        tableContainer.classList.remove('hidden');
        icon.classList.remove('bx-chevron-down');
        icon.classList.add('bx-chevron-up');
    } else {
        tableContainer.classList.add('hidden');
        icon.classList.remove('bx-chevron-up');
        icon.classList.add('bx-chevron-down');
    }
}

function toggleSemester(semId) {
    let content = document.getElementById('sem-' + semId);
    let icon = document.getElementById('sem-icon-' + semId);
    if (content.classList.contains('hidden')) {
        content.classList.remove('hidden');
        icon.classList.remove('bx-chevron-down');
        icon.classList.add('bx-chevron-up');
    } else {
        content.classList.add('hidden');
        icon.classList.remove('bx-chevron-up');
        icon.classList.add('bx-chevron-down');
    }
}

function deleteSelected() {
    let checkboxes = document.querySelectorAll('.record-cb:checked');
    let ids = Array.from(checkboxes).map(cb => parseInt(cb.value));
    
    if (ids.length === 0) {
        alert("Please select at least one record to delete.");
        return;
    }
    
    if (!confirm("Are you sure you want to delete " + ids.length + " records?")) return;
    
    fetch('/api/timetable/bulk_delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: ids })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            alert("Error: " + data.error);
        } else {
            alert(data.message);
            window.location.reload();
        }
    })
    .catch(err => {
        alert("A network error occurred.");
    });
}

function updateSelectedSubjectsUI() {
    const container = document.getElementById('selected-subjects-container');
    if (!container) return;
    
    container.innerHTML = '';
    const checkboxes = document.querySelectorAll('input[name="subjects"]:checked');
    
    Array.from(checkboxes).forEach(cb => {
        const code = cb.value;
        const name = cb.getAttribute('data-name');
        
        const badge = document.createElement('div');
        badge.className = 'selected-subject-badge';
        badge.style.cssText = 'background: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.4); color: white; padding: 0.4rem 0.8rem; border-radius: 20px; font-size: 0.85rem; display: flex; align-items: center; gap: 0.5rem; transition: all 0.2s ease; cursor: pointer;';
        
        badge.innerHTML = `<strong>${code}</strong> <i class='bx bx-x' style='font-size: 1.2rem; margin-top: 1px;'></i>`;
        
        // Add hover effect
        badge.onmouseover = () => badge.style.background = 'rgba(239, 68, 68, 0.3)';
        badge.onmouseout = () => badge.style.background = 'rgba(99, 102, 241, 0.2)';
        
        // Uncheck the checkbox when badge is clicked
        badge.onclick = () => {
            cb.checked = false;
            updateSelectedSubjectsUI();
        };
        
        container.appendChild(badge);
    });
}

function addBlacklistRule() {
    const container = document.getElementById('blacklist-rules-container');
    const ruleRow = document.createElement('div');
    ruleRow.className = 'blacklist-rule-row';
    ruleRow.style.cssText = 'display: grid; grid-template-columns: 1fr 1fr 1fr 1fr auto; gap: 0.5rem; align-items: center; background: rgba(0,0,0,0.3); padding: 0.8rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);';
    
    // Build subject options from currently selected subjects
    const checkboxes = document.querySelectorAll('input[name="subjects"]:checked');
    let subjectOptions = '<option value="ANY">Any Subject</option>';
    checkboxes.forEach(cb => {
        subjectOptions += `<option value="${cb.value}">${cb.value}</option>`;
    });

    ruleRow.innerHTML = `
        <select class="rule-subject premium-select" style="background: rgba(0,0,0,0.5); border: none; font-size: 0.85rem; padding: 0.5rem;">
            ${subjectOptions}
        </select>
        <input type="text" class="rule-section premium-input" placeholder="Sec (e.g. S1G1 or ANY)" style="background: rgba(0,0,0,0.5); border: none; font-size: 0.85rem; padding: 0.5rem; text-transform: uppercase;">
        <select class="rule-day premium-select" style="background: rgba(0,0,0,0.5); border: none; font-size: 0.85rem; padding: 0.5rem;">
            <option value="ANY">Any Day</option>
            <option value="Monday">Monday</option>
            <option value="Tuesday">Tuesday</option>
            <option value="Wednesday">Wednesday</option>
            <option value="Thursday">Thursday</option>
            <option value="Friday">Friday</option>
        </select>
        <div style="display: flex; align-items: center; gap: 0.3rem;">
            <input type="time" class="rule-start premium-input" style="background: rgba(0,0,0,0.5); border: none; font-size: 0.85rem; padding: 0.5rem;">
            <span style="color: var(--text-muted); font-size: 0.8rem;">to</span>
            <input type="time" class="rule-end premium-input" style="background: rgba(0,0,0,0.5); border: none; font-size: 0.85rem; padding: 0.5rem;">
        </div>
        <button type="button" onclick="this.parentElement.remove()" style="background: transparent; border: none; color: var(--error); cursor: pointer; font-size: 1.2rem; padding: 0.2rem;">
            <i class='bx bx-trash'></i>
        </button>
    `;
    container.appendChild(ruleRow);
}

function generateTimetable(allowCrossCourse = false) {
    const checkboxes = document.querySelectorAll('input[name="subjects"]:checked');
    const subjects = Array.from(checkboxes).map(cb => cb.value);
    
    if (subjects.length === 0) {
        alert("Please select at least one subject.");
        return;
    }

    const prefNoNight = document.getElementById('pref-no-night') ? document.getElementById('pref-no-night').checked : false;
    const prefNoMorning = document.getElementById('pref-no-morning') ? document.getElementById('pref-no-morning').checked : false;
    const prefFreeDay = document.getElementById('pref-free-day') ? document.getElementById('pref-free-day').value : "";
    let prefSection = document.getElementById('pref-section') ? document.getElementById('pref-section').value.trim() : "";
    if (prefSection) {
        prefSection = prefSection.toUpperCase();
    }
    
    // Collect Blacklist Rules
    const blacklistRules = [];
    const ruleRows = document.querySelectorAll('.blacklist-rule-row');
    ruleRows.forEach(row => {
        blacklistRules.push({
            subject: row.querySelector('.rule-subject').value,
            section: row.querySelector('.rule-section').value.trim().toUpperCase(),
            day: row.querySelector('.rule-day').value,
            start_time: row.querySelector('.rule-start').value,
            end_time: row.querySelector('.rule-end').value
        });
    });

    const loader = document.getElementById('generate-loader');
    loader.classList.remove('hidden');
    
    fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            subjects: subjects,
            no_night: prefNoNight,
            no_morning: prefNoMorning,
            free_day: prefFreeDay,
            preferred_group: prefSection,
            blocked_rules: blacklistRules,
            allow_cross_course: allowCrossCourse
        })
    })
    .then(r => r.json())
    .then(data => {
        loader.classList.add('hidden');
        const container = document.getElementById('results-container');
        const wrapper = document.getElementById('options-wrapper');
        const template = document.getElementById('timetable-option-template');
        
        container.classList.remove('hidden');
        wrapper.innerHTML = '';
        
        if (data.error || !data.valid_combinations || data.valid_combinations.length === 0) {
            if (!allowCrossCourse) {
                Swal.fire({
                    title: 'No Same-Course Options Found',
                    text: 'We couldn\\'t find a timetable within your own course that strictly satisfies your preferences. Would you like to try borrowing class groups from other courses?',
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonText: 'Yes, try other courses',
                    cancelButtonText: 'No, cancel',
                    confirmButtonColor: '#3085d6',
                    cancelButtonColor: '#d33'
                }).then((result) => {
                    if (result.isConfirmed) {
                        generateTimetable(true);
                    } else {
                        wrapper.innerHTML = '<p style="color: var(--error)">No conflict-free combinations available for the selected subjects.</p>';
                    }
                });
                return;
            } else {
                wrapper.innerHTML = '<p style="color: var(--error)">No conflict-free combinations available for the selected subjects.</p>';
                return;
            }
        }
        
        const warningBox = document.getElementById('preferred-group-warning');
        if (prefSection && data.perfect_match === false) {
            document.getElementById('warning-text').innerText = "Impossible to build a complete timetable using only " + prefSection + " due to clashes or missing classes. Showing the best alternative schedules using mixed sections.";
            warningBox.style.display = "block";
        } else {
            warningBox.style.display = "none";
        }

        data.valid_combinations.forEach((combo, index) => {
            window.currentRenderedCombos[index] = combo;
            const clone = template.content.cloneNode(true);
            clone.querySelector('.opt-num').textContent = index + 1;
            clone.querySelector('.opt-num-title').textContent = index + 1;
            
            const legendContainer = clone.querySelector('.subject-legend');
            const uniqueSubjects = {};
            
            const tbody = clone.querySelector('.tbody-content');
            
            // Initialize empty 15-hour matrix for each day
            let weekGrid = {
                "Monday": new Array(15).fill(null),
                "Tuesday": new Array(15).fill(null),
                "Wednesday": new Array(15).fill(null),
                "Thursday": new Array(15).fill(null),
                "Friday": new Array(15).fill(null),
                "Saturday": new Array(15).fill(null),
                "Sunday": new Array(15).fill(null)
            };
            
            combo.forEach(groupBundle => {
                groupBundle.classes.forEach(cls => {
                    let d = cls.day;
                    let st = parseInt(cls.start_time.substring(0, 2));
                    let et = parseInt(cls.end_time.substring(0, 2));
                    
                    let startIdx = st - 8;
                    let duration = et - st;
                    
                    if (weekGrid[d] && startIdx >= 0 && startIdx < 15) {
                        weekGrid[d][startIdx] = { ...cls, duration: duration };
                        for(let i=1; i<duration; i++){
                            if(startIdx + i < 15) weekGrid[d][startIdx + i] = "BLOCKED";
                        }
                    }
                    
                    // Collect unique subjects for the legend
                    if (cls.subject_code && !uniqueSubjects[cls.subject_code]) {
                        uniqueSubjects[cls.subject_code] = cls.subject_name;
                    }
                });
            });
            const legendTbody = clone.querySelector('.legend-tbody');
            
            if (legendTbody) {
                Object.keys(uniqueSubjects).forEach(code => {
                    const tr = document.createElement('tr');
                    tr.style.borderBottom = '1px solid #f1f5f9';
                    tr.innerHTML = `
                        <td style="padding: 0.5rem; font-weight: 600; color: var(--primary);">${code}</td>
                        <td style="padding: 0.5rem; color: #475569;">${uniqueSubjects[code]}</td>
                    `;
                    legendTbody.appendChild(tr);
                });
            }
            
            // Inject intelligent Break Spacers into common lunch hours IF they are not blocked by a class
            const standardDays = ["Monday", "Tuesday", "Wednesday", "Thursday"];
            standardDays.forEach(d => {
                if (weekGrid[d][5] === null) { // 13:00 is slot index 5 (13 - 8)
                    weekGrid[d][5] = { isBreak: true, duration: 1, text: "BREAK" };
                }
            });
            
            // Friday Jumaat Break 12:00 - 15:00 (index 4,5,6)
            if (weekGrid["Friday"][4] === null && weekGrid["Friday"][5] === null && weekGrid["Friday"][6] === null) {
                weekGrid["Friday"][4] = { isBreak: true, duration: 3, text: "FRIDAY BREAK" };
                weekGrid["Friday"][5] = "BLOCKED";
                weekGrid["Friday"][6] = "BLOCKED";
            } else {
                // If it is partially obstructed, inject single hour breaks into whatever is free
                for(let i=4; i<=6; i++) {
                    if (weekGrid["Friday"][i] === null) {
                        weekGrid["Friday"][i] = { isBreak: true, duration: 1, text: "BREAK" };
                    }
                }
            }
            
            // Render to DOM
            const daysList = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
            daysList.forEach(day => {
                let isEmpty = weekGrid[day].every(c => c === null);
                if((day === "Sunday" || day === "Saturday") && isEmpty) return; // Skip completely empty weekends
                
                const tr = document.createElement('tr');
                tr.innerHTML = `<td style="font-weight: 600; color: var(--secondary);">${day}</td>`;
                
                for(let i=0; i<15; i++) {
                    let cell = weekGrid[day][i];
                    if (cell === "BLOCKED") continue;
                    
                    const td = document.createElement('td');
                    if (cell === null) {
                        td.className = "time-cell-empty";
                        tr.appendChild(td);
                    } else if (cell.isBreak) {
                        td.colSpan = cell.duration;
                        td.className = "time-cell-filled type-default";
                        td.style.backgroundColor = "#e2e8f0";
                        td.style.border = "none";
                        td.innerHTML = `<div style="font-weight: 700; opacity: 0.6; letter-spacing: 2px;">${cell.text}</div>`;
                        tr.appendChild(td);
                    } else {
                        td.colSpan = cell.duration;
                        td.className = `time-cell-filled type-${cell.class_type.replace(/[^a-zA-Z]/g, '')}`;
                        td.innerHTML = `
                            <div class="cell-content">
                                <span class="cell-subject">${cell.subject_code}</span>
                                <span class="cell-meta">${cell.class_type} | ${cell.group_name} ${cell.course_code ? '(' + cell.course_code + ')' : ''} | ${cell.room}</span>
                                <span class="cell-meta" style="font-weight: 500;">
                                    ${cell.lecturer_name ? `<a href="#" onclick="draftLecturerEmail(event, ${index}, '${cell.subject_code}', '${cell.lecturer_name.replace(/'/g, "\\'")}'); return false;" style="color: #0284c7; text-decoration: underline; cursor: pointer;">${cell.lecturer_name}</a>` : ''}
                                </span>
                            </div>
                        `;
                        tr.appendChild(td);
                    }
                }
                tbody.appendChild(tr);
            });
            // Attach save event listener with the specific combo data
            const saveBtn = clone.querySelector('.save-timetable-btn');
            saveBtn.onclick = function() {
                saveTimetable(combo, this);
            };
            
            wrapper.appendChild(clone);
        });
    })
    .catch(err => {
        loader.classList.add('hidden');
        alert("An error occurred while generating timetables.");
    });
}

function filterStudentSubjects() {
    let input = document.getElementById('student-subject-search').value.toUpperCase();
    let grid = document.getElementById('student-checkbox-grid');
    if (!grid) return;
    
    let labels = grid.getElementsByTagName('label');
    for (let i = 0; i < labels.length; i++) {
        let textContent = labels[i].textContent || labels[i].innerText;
        if (textContent.toUpperCase().indexOf(input) > -1) {
            labels[i].style.display = "";
        } else {
            labels[i].style.display = "none";
        }
    }
}

function editRow(btn, id) {
    const row = document.getElementById('row-' + id);
    const cells = row.querySelectorAll('td[data-field]');
    
    cells.forEach(td => {
        const field = td.getAttribute('data-field');
        const val = td.innerText.trim();
        
        if (field === 'time') {
            const start = td.getAttribute('data-start') || '';
            const end = td.getAttribute('data-end') || '';
            td.innerHTML = `
                <div style="display: flex; flex-direction: column; gap: 0.2rem;">
                    <input type="time" class="edit-input time-start" value="${start}" style="padding: 0.2rem; border-radius: 4px; border: 1px solid #ccc; background: #fff; color: #000; font-size: 0.8rem;">
                    <input type="time" class="edit-input time-end" value="${end}" style="padding: 0.2rem; border-radius: 4px; border: 1px solid #ccc; background: #fff; color: #000; font-size: 0.8rem;">
                </div>
            `;
        } else {
            td.innerHTML = `<input type="text" class="edit-input" data-key="${field}" value="${val}" style="width: 100%; min-width: 80px; padding: 0.2rem; border-radius: 4px; border: 1px solid #ccc; background: #fff; color: #000; font-size: 0.8rem;">`;
        }
    });
    
    btn.innerText = 'Save';
    btn.style.backgroundColor = '#22c55e';
    btn.setAttribute('onclick', `saveRow(this, ${id})`);
}

function saveRow(btn, id) {
    const row = document.getElementById('row-' + id);
    const payload = { id: id };
    
    const textInputs = row.querySelectorAll('input[type="text"].edit-input');
    textInputs.forEach(input => {
        payload[input.getAttribute('data-key')] = input.value.trim();
    });
    
    const timeStart = row.querySelector('.time-start');
    const timeEnd = row.querySelector('.time-end');
    if (timeStart && timeEnd) {
        payload['start_time'] = timeStart.value;
        payload['end_time'] = timeEnd.value;
    }
    
    btn.innerText = 'Saving...';
    
    fetch('/api/timetable/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error: ' + data.error);
            btn.innerText = 'Save';
        } else {
            const cells = row.querySelectorAll('td[data-field]');
            cells.forEach(td => {
                const field = td.getAttribute('data-field');
                if (field === 'time') {
                    td.setAttribute('data-start', payload['start_time']);
                    td.setAttribute('data-end', payload['end_time']);
                    td.innerHTML = `${payload['start_time']} - ${payload['end_time']}`;
                } else {
                    td.innerHTML = payload[field];
                }
                
                if (payload[field] && !payload[field].toUpperCase().includes('UNKNOWN')) {
                    td.classList.remove('alert-danger');
                }
            });
            
            btn.innerText = 'Edit';
            btn.style.backgroundColor = '';
            btn.setAttribute('onclick', `editRow(this, ${id})`);
            
            // Auto-sync other DOM elements impacted by global propagation
            if (data.updated_ids && data.subject_name) {
                data.updated_ids.forEach(affected_id => {
                    if (affected_id !== id) {
                        const affectedRow = document.getElementById('row-' + affected_id);
                        if (affectedRow) {
                            const nameCell = affectedRow.querySelector('td[data-field="subject_name"]');
                            if (nameCell) {
                                nameCell.innerHTML = data.subject_name;
                                nameCell.classList.remove('alert-danger');
                            }
                        }
                    }
                });
            }
            
            // Intelligent Badge Cleanup: Scan affected Course blocks to see if all errors are resolved
            const updatedSections = new Set();
            updatedSections.add(row.closest('.course-section'));
            
            if (data.updated_ids) {
                data.updated_ids.forEach(affected_id => {
                    const affectedRow = document.getElementById('row-' + affected_id);
                    if (affectedRow) {
                        const sec = affectedRow.closest('.course-section');
                        if (sec) updatedSections.add(sec);
                    }
                });
            }
            
            updatedSections.forEach(sec => {
                if (!sec) return;
                const remainingAlerts = sec.querySelectorAll('td.alert-danger');
                if (remainingAlerts.length === 0) {
                    const header = sec.querySelector('.course-header');
                    if (header) {
                        header.classList.remove('alert-danger');
                        header.style.border = '';
                        const badge = header.querySelector('.error-badge');
                        if (badge) badge.remove();
                    }
                }
            });
        }
    })
    .catch(err => {
        console.error(err);
        alert('Failed to save changes.');
        btn.innerText = 'Save';
    });
}

function saveTimetable(comboData, btnElement) {
    const originalText = btnElement.innerHTML;
    btnElement.innerHTML = "<i class='bx bx-loader-alt bx-spin'></i> Saving...";
    btnElement.disabled = true;

    fetch('/api/timetable/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ timetable_data: comboData })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            btnElement.innerHTML = originalText;
            btnElement.disabled = false;
        } else {
            btnElement.innerHTML = "<i class='bx bxs-check-circle'></i> Saved!";
            btnElement.classList.add('success-save');
            btnElement.style.background = "#10B981"; // Turn green
        }
    })
    .catch(err => {
        alert("Network error.");
        btnElement.innerHTML = originalText;
        btnElement.disabled = false;
    });
}

function draftLecturerEmail(event, index, subjectCode, lecturerName) {
    event.stopPropagation();
    
    const combo = window.currentRenderedCombos[index];
    let scheduleStrings = [];
    let subjectNameFull = subjectCode;
    
    if (combo) {
        combo.forEach(bundle => {
            bundle.classes.forEach(cls => {
                if (cls.subject_code === subjectCode) {
                    scheduleStrings.push(`${cls.class_type}: ${cls.day}, ${cls.start_time.substring(0, 5)} - ${cls.end_time.substring(0, 5)}`);
                    if (cls.subject_name) {
                        subjectNameFull = `${cls.subject_code} ${cls.subject_name}`;
                    }
                }
            });
        });
    }
    
    const scheduleBlock = scheduleStrings.join('\n');
    const userName = (typeof CURRENT_USER_NAME !== 'undefined' && CURRENT_USER_NAME) ? CURRENT_USER_NAME : 'Student';
    const userMatric = (typeof CURRENT_USER_MATRIC !== 'undefined' && CURRENT_USER_MATRIC) ? CURRENT_USER_MATRIC : '';
    
    const subjectLine = `Request to Join ${subjectNameFull} Class`;
    const body = `Dear Sir/Madam,

Good day.

My name is ${userName} (${userMatric}). I would like to kindly request permission to join your ${subjectNameFull} class at the following schedule:

${scheduleBlock}

Due to timetable clashes with my other subjects, the above-mentioned schedule is the only slot that fits correctly into my current timetable. Therefore, I would sincerely appreciate your consideration in allowing me to join this subject at the specified time.

Thank you for your time and consideration.

Yours sincerely,
${userName}
${userMatric}`;

    const originalText = event.target.innerText;
    event.target.innerHTML = "<i class='bx bx-loader-alt bx-spin'></i>";
    
    fetch('/api/student/lecturer_email?name=' + encodeURIComponent(lecturerName))
    .then(r => r.json())
    .then(data => {
        event.target.innerText = originalText;
        const toEmail = data.email || '';
        const mailtoUrl = `mailto:${toEmail}?subject=${encodeURIComponent(subjectLine)}&body=${encodeURIComponent(body)}`;
        window.location.href = mailtoUrl;
    })
    .catch(err => {
        event.target.innerText = originalText;
        const mailtoUrl = `mailto:?subject=${encodeURIComponent(subjectLine)}&body=${encodeURIComponent(body)}`;
        window.location.href = mailtoUrl;
    });
}

function openSavedModal() {
    document.getElementById('saved-modal').classList.remove('hidden');
    loadSavedTimetables();
}

function closeSavedModal() {
    document.getElementById('saved-modal').classList.add('hidden');
}

function loadSavedTimetables() {
    const loader = document.getElementById('saved-loader');
    const wrapper = document.getElementById('saved-options-wrapper');
    const template = document.getElementById('timetable-option-template');
    
    loader.style.display = 'block';
    wrapper.innerHTML = '';
    
    fetch('/api/timetable/saved')
    .then(r => r.json())
    .then(res => {
        loader.style.display = 'none';
        
        if (res.error) {
            wrapper.innerHTML = `<p style="color: red;">${res.error}</p>`;
            return;
        }
        
        if (res.data.length === 0) {
            wrapper.innerHTML = `<div style="text-align: center; color: white; padding: 2rem;">
                <i class='bx bx-ghost' style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                <p>You haven't saved any timetables yet.</p>
            </div>`;
            return;
        }
        
        res.data.forEach((savedItem, index) => {
            const combo = savedItem.data;
            window.currentRenderedCombos[index] = combo;
            const clone = template.content.cloneNode(true);
            
            // Adjust header for saved view
            const headerNum = clone.querySelector('.opt-num');
            if (headerNum) headerNum.textContent = `(Saved on ${savedItem.created_at.split(' ')[0]})`;
            
            const titleNum = clone.querySelector('.opt-num-title');
            if (titleNum) titleNum.textContent = `Saved`;
            
            const legendContainer = clone.querySelector('.subject-legend');
            const uniqueSubjects = {};
            
            // Swap "Save" button for "Delete" button
            const btnContainer = clone.querySelector('.card-header > div:last-child');
            if (btnContainer) {
                const saveBtn = btnContainer.querySelector('.save-timetable-btn');
                if (saveBtn) {
                    saveBtn.className = "btn-primary delete-saved-btn";
                    saveBtn.style.background = "#EF4444"; // Red
                    saveBtn.innerHTML = "<i class='bx bxs-trash'></i> Remove";
                    saveBtn.onclick = function() {
                        deleteSavedTimetable(savedItem.id, this);
                    };
                }
                
                // Add Primary button
                const primaryBtn = document.createElement('button');
                primaryBtn.className = "btn-primary";
                if (savedItem.is_primary) {
                    primaryBtn.style.background = "#F59E0B";
                    primaryBtn.style.color = "white";
                    primaryBtn.innerHTML = "<i class='bx bxs-star'></i> Primary";
                    primaryBtn.disabled = true;
                } else {
                    primaryBtn.style.background = "var(--surface-border)";
                    primaryBtn.innerHTML = "<i class='bx bx-star'></i> Set Primary";
                    primaryBtn.onclick = function() {
                        setPrimaryTimetable(savedItem.id, this);
                    };
                }
                btnContainer.prepend(primaryBtn);
            }
            
            // Reconstruct the Grid Matrix identically to generation
            const tbody = clone.querySelector('.tbody-content');
            let weekGrid = {
                "Monday": new Array(15).fill(null),
                "Tuesday": new Array(15).fill(null),
                "Wednesday": new Array(15).fill(null),
                "Thursday": new Array(15).fill(null),
                "Friday": new Array(15).fill(null),
                "Saturday": new Array(15).fill(null),
                "Sunday": new Array(15).fill(null)
            };
            
            combo.forEach(groupBundle => {
                groupBundle.classes.forEach(cls => {
                    let d = cls.day;
                    let st = parseInt(cls.start_time.substring(0, 2));
                    let et = parseInt(cls.end_time.substring(0, 2));
                    
                    let startIdx = st - 8;
                    let duration = et - st;
                    
                    if (weekGrid[d] && startIdx >= 0 && startIdx < 15) {
                        weekGrid[d][startIdx] = { ...cls, duration: duration };
                        for(let i=1; i<duration; i++){
                            if(startIdx + i < 15) weekGrid[d][startIdx + i] = "BLOCKED";
                        }
                    }
                    
                    if (cls.subject_code && !uniqueSubjects[cls.subject_code]) {
                        uniqueSubjects[cls.subject_code] = cls.subject_name;
                    }
                });
            });
            
            const legendTbody = clone.querySelector('.legend-tbody');
            if (legendTbody) {
                Object.keys(uniqueSubjects).forEach(code => {
                    const tr = document.createElement('tr');
                    tr.style.borderBottom = '1px solid #f1f5f9';
                    tr.innerHTML = `
                        <td style="padding: 0.5rem; font-weight: 600; color: var(--primary);">${code}</td>
                        <td style="padding: 0.5rem; color: #475569;">${uniqueSubjects[code]}</td>
                    `;
                    legendTbody.appendChild(tr);
                });
            }
            
            const standardDays = ["Monday", "Tuesday", "Wednesday", "Thursday"];
            standardDays.forEach(d => {
                if (weekGrid[d][5] === null) {
                    weekGrid[d][5] = { isBreak: true, duration: 1, text: "BREAK" };
                }
            });
            
            if (weekGrid["Friday"][4] === null && weekGrid["Friday"][5] === null && weekGrid["Friday"][6] === null) {
                weekGrid["Friday"][4] = { isBreak: true, duration: 3, text: "FRIDAY BREAK" };
                weekGrid["Friday"][5] = "BLOCKED";
                weekGrid["Friday"][6] = "BLOCKED";
            } else {
                for(let i=4; i<=6; i++) {
                    if (weekGrid["Friday"][i] === null) {
                        weekGrid["Friday"][i] = { isBreak: true, duration: 1, text: "BREAK" };
                    }
                }
            }
            
            const daysList = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
            daysList.forEach(day => {
                let isEmpty = weekGrid[day].every(c => c === null);
                if((day === "Sunday" || day === "Saturday") && isEmpty) return;
                
                const tr = document.createElement('tr');
                tr.innerHTML = `<td style="font-weight: 600; color: var(--secondary);">${day}</td>`;
                
                for(let i=0; i<15; i++) {
                    let cell = weekGrid[day][i];
                    if (cell === "BLOCKED") continue;
                    
                    const td = document.createElement('td');
                    if (cell === null) {
                        td.className = "time-cell-empty";
                        tr.appendChild(td);
                    } else if (cell.isBreak) {
                        td.colSpan = cell.duration;
                        td.className = "time-cell-filled type-default";
                        td.style.backgroundColor = "#e2e8f0";
                        td.style.border = "none";
                        td.innerHTML = `<div style="font-weight: 700; opacity: 0.6; letter-spacing: 2px;">${cell.text}</div>`;
                        tr.appendChild(td);
                    } else {
                        td.colSpan = cell.duration;
                        td.className = `time-cell-filled type-${cell.class_type.replace(/[^a-zA-Z]/g, '')}`;
                        td.innerHTML = `
                            <div class="cell-content">
                                <span class="cell-subject">${cell.subject_code}</span>
                                <span class="cell-meta">${cell.class_type} | ${cell.group_name} | ${cell.room}</span>
                                <span class="cell-meta" style="font-weight: 500;">
                                    ${cell.lecturer_name ? `<a href="#" onclick="draftLecturerEmail(event, ${index}, '${cell.subject_code}', '${cell.lecturer_name.replace(/'/g, "\\'")}'); return false;" style="color: #0284c7; text-decoration: underline; cursor: pointer;">${cell.lecturer_name}</a>` : ''}
                                </span>
                            </div>
                        `;
                        tr.appendChild(td);
                    }
                }
                tbody.appendChild(tr);
            });
            
            wrapper.appendChild(clone);
        });
    })
    .catch(err => {
        loader.style.display = 'none';
        alert("Failed to load saved timetables.");
    });
}

function deleteSavedTimetable(id, btnElement) {
    if (!confirm("Are you sure you want to remove this timetable from your favorites?")) return;
    
    const card = btnElement.closest('.result-card');
    card.style.opacity = '0.5';
    
    fetch('/api/timetable/saved/' + id, {
        method: 'DELETE'
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            card.style.opacity = '1';
        } else {
            card.remove();
        }
    })
    .catch(err => {
        alert("Network error.");
        card.style.opacity = '1';
    });
}

function downloadImage(btnElement) {
    const card = btnElement.closest('.result-card');
    const target = card.querySelector('.timetable-render-target');
    const originalText = btnElement.innerHTML;
    
    btnElement.innerHTML = "<i class='bx bx-loader-alt bx-spin'></i> Rendering...";
    btnElement.disabled = true;
    
    // Temporarily enforce styles for a clean capture
    const wrapper = btnElement.closest('.result-card').querySelector('.timetable-grid-wrapper');
    html2canvas(wrapper, { scale: 2 }).then(canvas => {
        const link = document.createElement('a');
        link.download = 'FTMK_Timetable.png';
        link.href = canvas.toDataURL();
        link.click();
        btnElement.innerHTML = originalText;
        btnElement.disabled = false;
    });
}


function setPrimaryTimetable(savedId, btnElement) {
    const originalText = btnElement.innerHTML;
    btnElement.innerHTML = "<i class='bx bx-loader-alt bx-spin'></i>";
    btnElement.disabled = true;

    fetch('/api/timetable/set_primary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: savedId })
    })
    .then(r => r.json())
    .then(res => {
        if (res.error) {
            alert(res.error);
            btnElement.innerHTML = originalText;
            btnElement.disabled = false;
        } else {
            loadSavedTimetables();
        }
    })
    .catch(err => {
        alert("Network error.");
        btnElement.innerHTML = originalText;
        btnElement.disabled = false;
    });
}
