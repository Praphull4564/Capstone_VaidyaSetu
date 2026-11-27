const form = document.querySelector('#schedule-form');
const prescriptionInput = document.querySelector('#prescription');
const routineInput = document.querySelector('#routine');
const characterCount = document.querySelector('#character-count');
const submitButton = document.querySelector('#submit-button');
const formError = document.querySelector('#form-error');
const results = document.querySelector('#results');
const scheduleRows = document.querySelector('#schedule-rows');
const notices = document.querySelector('#notices');
const calendarDate = document.querySelector('#calendar-date');
const calendarEvents = document.querySelector('#calendar-events');
let currentSchedule = null;

prescriptionInput.addEventListener('input', () => {
  characterCount.textContent = `${prescriptionInput.value.length} / 12000`;
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  formError.hidden = true;
  submitButton.disabled = true;
  submitButton.querySelector('.button-label').textContent = 'Preparing your schedule...';

  try {
    const response = await fetch('/api/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prescription: prescriptionInput.value,
        routine: routineInput.value,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The schedule could not be prepared.');
    currentSchedule = data;
    renderSchedule(data);
    results.hidden = false;
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    formError.textContent = error.message || 'A network error occurred. Check your connection and try again.';
    formError.hidden = false;
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector('.button-label').textContent = 'Prepare my schedule';
  }
});

document.querySelector('#new-schedule').addEventListener('click', () => {
  results.hidden = true;
  currentSchedule = null;
  prescriptionInput.focus();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

calendarDate.addEventListener('change', renderCalendarEvents);

function appendCell(row, value) {
  const cell = document.createElement('td');
  cell.textContent = value || 'Not provided';
  row.append(cell);
}

function renderSchedule(schedule) {
  scheduleRows.replaceChildren();
  notices.replaceChildren();
  const messages = [
    ...(schedule.warnings || []).map((text) => ({ text, type: 'warning' })),
    ...(schedule.missing_information || []).map((text) => ({ text: `Please confirm: ${text}`, type: 'missing' })),
  ];

  messages.forEach(({ text, type }) => {
    const notice = document.createElement('div');
    notice.className = `notice${type === 'missing' ? ' missing' : ''}`;
    notice.textContent = text;
    notices.append(notice);
  });

  if (!schedule.medications.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.className = 'empty-schedule';
    cell.colSpan = 5;
    cell.textContent = 'No medication details could be extracted. Check the prescription text or ask your prescriber or pharmacist.';
    row.append(cell);
    scheduleRows.append(row);
  } else {
    schedule.medications.forEach((medicine) => {
      const row = document.createElement('tr');
      const times = medicine.reminders?.length
        ? medicine.reminders.map((reminder) => reminder.time || reminder.label).filter(Boolean).join(', ')
        : medicine.frequency === 'As needed' || /\b(as needed|prn)\b/i.test(medicine.frequency)
          ? 'As needed; no fixed reminder'
          : 'Not specified';
      appendCell(row, medicine.name);
      appendCell(row, medicine.dose);
      appendCell(row, times);
      appendCell(row, medicine.food_relation);
      appendCell(row, medicine.duration);
      scheduleRows.append(row);
    });
  }

  const summary = schedule.medications.flatMap((medicine) =>
    (medicine.reminders || []).map((reminder) => `${medicine.name}: ${reminder.label || reminder.time}${reminder.time && reminder.label ? ` (${reminder.time})` : ''}`),
  );
  document.querySelector('#reminder-summary-text').textContent = summary.length
    ? summary.join(' · ')
    : 'No fixed reminders were created. Follow the prescription and confirm any missing or unclear timing with your doctor or pharmacist.';
  document.querySelector('#json-output').textContent = JSON.stringify(schedule, null, 2);
  calendarDate.value = '';
  calendarEvents.replaceChildren();
}

function renderCalendarEvents() {
  calendarEvents.replaceChildren();
  if (!currentSchedule) return;
  if (!calendarDate.value) {
    const note = document.createElement('p');
    note.className = 'calendar-empty';
    note.textContent = 'Choose the date you want these reminders to appear on.';
    calendarEvents.append(note);
    return;
  }

  const timedReminders = currentSchedule.medications.flatMap((medicine) =>
    (medicine.reminders || [])
      .filter((reminder) => /^([01]\d|2[0-3]):[0-5]\d$/.test(reminder.time))
      .map((reminder) => ({ medicine, reminder })),
  );

  if (!timedReminders.length) {
    const note = document.createElement('p');
    note.className = 'calendar-empty';
    note.textContent = 'No exact clock times are available to add. Confirm timing with your prescriber before creating calendar reminders.';
    calendarEvents.append(note);
    return;
  }

  timedReminders.forEach(({ medicine, reminder }) => {
    const [year, month, day] = calendarDate.value.split('-');
    const [hour, minute] = reminder.time.split(':');
    const start = `${year}${month}${day}T${hour}${minute}00`;
    const endDate = new Date(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute) + 15);
    const end = `${endDate.getFullYear()}${String(endDate.getMonth() + 1).padStart(2, '0')}${String(endDate.getDate()).padStart(2, '0')}T${String(endDate.getHours()).padStart(2, '0')}${String(endDate.getMinutes()).padStart(2, '0')}00`;
    const details = [
      reminder.label,
      `Dose: ${medicine.dose}`,
      medicine.food_relation ? `Food: ${medicine.food_relation}` : '',
      medicine.special_instructions ? `Doctor's instructions: ${medicine.special_instructions}` : '',
      'Confirm this reminder against your prescription.',
    ].filter(Boolean).join('\n');
    const params = new URLSearchParams({
      action: 'TEMPLATE',
      text: `Medication reminder: ${medicine.name}`,
      dates: `${start}/${end}`,
      details,
    });
    const link = document.createElement('a');
    link.className = 'calendar-link';
    link.href = `https://calendar.google.com/calendar/render?${params.toString()}`;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = `Add ${medicine.name} · ${reminder.time} to Google Calendar`;
    calendarEvents.append(link);
  });
}