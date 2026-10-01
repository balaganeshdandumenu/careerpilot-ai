const panels = [...document.querySelectorAll('[data-step-panel]')];
const indicators = [...document.querySelectorAll('[data-step-indicator]')];
const stepCount = document.querySelector('#step-count');
const stepTitle = document.querySelector('#step-title');
const stepDescription = document.querySelector('#step-description');
const railFill = document.querySelector('#rail-fill');
const backButton = document.querySelector('#wizard-back');
const nextButton = document.querySelector('#wizard-next');
const submitButton = document.querySelector('#wizard-submit');
const skillEntry = document.querySelector('#skill-entry');
const skillChips = document.querySelector('#skill-chip-list');
const skillInputs = document.querySelector('#skill-hidden-inputs');
let currentStep = 1;

const stepCopy = [
  ['About you', 'A name helps make your plan feel like yours.'],
  ['Your direction', 'Pick a role and tell us where you’re starting from.'],
  ['Skills you have', 'Your current skills are the first markers on the path.'],
  ['Your background', 'Projects and experience help put skills in context.'],
  ['Your schedule', 'A useful plan fits the time you really have.'],
  ['How you learn', 'Your preferences shape the kind of practice you see.'],
];

function updateStep(step) {
  currentStep = step;
  panels.forEach((panel) => {
    const active = Number(panel.dataset.stepPanel) === step;
    panel.hidden = !active;
    panel.classList.toggle('is-active', active);
  });
  indicators.forEach((indicator) => {
    const number = Number(indicator.dataset.stepIndicator);
    indicator.classList.toggle('is-current', number === step);
    indicator.classList.toggle('is-complete', number < step);
    if (number === step) indicator.setAttribute('aria-current', 'step');
    else indicator.removeAttribute('aria-current');
  });
  stepCount.textContent = String(step).padStart(2, '0');
  stepTitle.textContent = stepCopy[step - 1][0];
  stepDescription.textContent = stepCopy[step - 1][1];
  railFill.style.height = `${((step - 1) / 5) * 100}%`;
  backButton.disabled = step === 1;
  nextButton.hidden = step === panels.length;
  submitButton.hidden = step !== panels.length;
  panels[step - 1].querySelector('input:not([type=hidden]), select, textarea, button')?.focus({ preventScroll: true });
}

function validateStep(step) {
  const panel = panels[step - 1];
  const field = panel.querySelector('[required]');
  if (field && !field.value.trim()) {
    field.setAttribute('aria-invalid', 'true');
    field.focus();
    field.addEventListener('input', () => field.removeAttribute('aria-invalid'), { once: true });
    return false;
  }
  if (step === 5) {
    const hours = Number(panel.querySelector('[name=hours_per_day]').value);
    if (hours < 0.25 || hours > 12) {
      const input = panel.querySelector('[name=hours_per_day]');
      input.setAttribute('aria-invalid', 'true');
      input.focus();
      return false;
    }
  }
  return true;
}

nextButton.addEventListener('click', () => {
  if (validateStep(currentStep) && currentStep < panels.length) updateStep(currentStep + 1);
});
backButton.addEventListener('click', () => updateStep(Math.max(1, currentStep - 1)));

document.querySelector('#career-form').addEventListener('submit', (event) => {
  if (!validateStep(currentStep)) {
    event.preventDefault();
    return;
  }
  document.querySelector('#save-status').textContent = 'Building your plan…';
  submitButton.disabled = true;
});

function addSkill(value) {
  const skill = value.trim().replace(/\s+/g, ' ');
  if (!skill || skill.length > 40) return;
  const existing = [...skillInputs.querySelectorAll('input')].some((input) => input.value.toLowerCase() === skill.toLowerCase());
  if (existing || skillInputs.querySelectorAll('input').length >= 30) return;
  const input = document.createElement('input');
  input.type = 'hidden';
  input.name = 'skills';
  input.value = skill;
  skillInputs.append(input);

  const chip = document.createElement('span');
  chip.className = 'skill-chip';
  const label = document.createElement('span');
  label.textContent = skill;
  const remove = document.createElement('button');
  remove.type = 'button';
  remove.setAttribute('aria-label', `Remove ${skill}`);
  remove.textContent = '×';
  remove.addEventListener('click', () => {
    input.remove();
    chip.remove();
  });
  chip.append(label, remove);
  skillChips.append(chip);
}

const savedSkills = [...skillInputs.querySelectorAll('input')].map((input) => input.value);
skillInputs.replaceChildren();
savedSkills.forEach(addSkill);
document.querySelector('#add-skill').addEventListener('click', () => {
  addSkill(skillEntry.value);
  skillEntry.value = '';
  skillEntry.focus();
});
skillEntry.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    event.preventDefault();
    document.querySelector('#add-skill').click();
  }
});
document.querySelectorAll('.skill-suggestion').forEach((button) => button.addEventListener('click', () => addSkill(button.dataset.skill)));

const invalidPanel = document.querySelector('.wizard-panel .has-error, .wizard-panel [aria-invalid="true"]')?.closest('[data-step-panel]');
updateStep(invalidPanel ? Number(invalidPanel.dataset.stepPanel) : 1);