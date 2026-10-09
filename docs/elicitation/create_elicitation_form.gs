/**
 * Builds the requirement-elicitation questionnaire as a Google Form.
 *
 * How to run (once):
 *   1. Go to https://script.google.com and click "New project".
 *   2. Delete the sample code, paste this whole file, and fill in the five
 *      values in SETTINGS below.
 *   3. Click Run (function: createElicitationForm) and allow access when
 *      Google asks. The script only creates a form and a response sheet in
 *      your own Drive.
 *   4. Open View > Logs (or Execution log) to get the edit link, the
 *      respondent link and the response-sheet link.
 *
 * The form is created but not shared. Do not send the respondent link until
 * ethics approval is granted. If ETHICS_REF was not known when you ran the
 * script, add it to the form description by hand.
 */

var SETTINGS = {
  STUDENT_NAME: '[Your name]',
  UNIVERSITY: '[University name]',
  SUPERVISOR: '[Supervisor name]',
  CONTACT_EMAIL: '[your university email]',
  ETHICS_REF: '[ethics approval reference]',
};

var AGREE_5 = ['Strongly disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly agree', 'Not sure'];

function createElicitationForm() {
  var s = SETTINGS;
  var form = FormApp.create('Private search across hospitals: requirements survey');

  form.setDescription(
    'You are invited to take part in a short survey (about 7 minutes) for a final-year ' +
    'research project at ' + s.UNIVERSITY + ', carried out by ' + s.STUDENT_NAME +
    ' and supervised by ' + s.SUPERVISOR + '.\n\n' +
    'The project studies how a user could search records or documents held by several ' +
    'hospitals or organisations without revealing their question, or which ' +
    'organisations they searched. Your answers will help set the requirements for a ' +
    'prototype.\n\n' +
    'Taking part is voluntary. The survey is anonymous: it does not ask for your name ' +
    'or email address. Please use made-up examples only and do not enter patient ' +
    'details, passwords or confidential information. Because answers are anonymous, a ' +
    'response cannot be withdrawn after you submit it. Only overall results will be ' +
    'reported, and the data will be deleted when the project ends.\n\n' +
    'Questions: ' + s.CONTACT_EMAIL + '. Ethics approval reference: ' + s.ETHICS_REF + '.'
  );
  form.setCollectEmail(false);
  form.setProgressBar(true);
  form.setAllowResponseEdits(false);
  form.setShowLinkToRespondAgain(false);
  form.setConfirmationMessage(
    'Thank you for taking part. If you are willing to do a 20 to 30 minute follow-up ' +
    'interview, please email ' + s.CONTACT_EMAIL + '.'
  );

  // Section A: consent
  var consent = form.addMultipleChoiceItem()
    .setTitle('Consent')
    .setHelpText('I am 18 or over, I have read the information above, and I agree to take part.')
    .setRequired(true);
  consent.setChoices([
    consent.createChoice('Yes, I agree to take part', FormApp.PageNavigationType.CONTINUE),
    consent.createChoice('No, I do not want to take part', FormApp.PageNavigationType.SUBMIT),
  ]);

  // Section B: about you
  form.addPageBreakItem().setTitle('About you');

  form.addMultipleChoiceItem()
    .setTitle('Which role best describes you?')
    .setChoiceValues([
      'Clinician or healthcare practitioner',
      'Medical or health researcher',
      'Hospital IT or records administrator',
      'Software developer, data scientist or AI/ML engineer',
      'Security, privacy or data protection professional',
      'Student',
    ])
    .showOtherOption(true)
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('How many years of experience do you have in that role?')
    .setChoiceValues(['Less than 1 year', '1 to 3 years', '4 to 10 years', 'More than 10 years']);

  form.addMultipleChoiceItem()
    .setTitle('How often do you need information held by more than one organisation or database?')
    .setChoiceValues(['Never', 'Rarely', 'Monthly', 'Weekly', 'Daily', 'Not sure']);

  // Section C: what needs protecting (Gaps 1 and 2)
  form.addPageBreakItem()
    .setTitle('What needs protecting')
    .setHelpText('Imagine a tool that searches the records of several hospitals for you.');

  form.addCheckboxItem()
    .setTitle('In your setting, which of these would need protecting? (select all that apply)')
    .setChoiceValues([
      'The question I type',
      'Which hospitals or databases I search',
      'The records or documents that come back',
      'Who is asking (my identity)',
      'None of these',
      'Not sure',
    ]);

  form.addScaleItem()
    .setTitle('How concerned would you be if a hospital could read the exact question you searched?')
    .setBounds(1, 5)
    .setLabels('Not concerned', 'Very concerned');

  form.addScaleItem()
    .setTitle('An observer cannot read your question, but can see that you searched only the ' +
              'cancer (oncology) records of two hospitals. How concerned would you be?')
    .setBounds(1, 5)
    .setLabels('Not concerned', 'Very concerned');

  form.addParagraphTextItem()
    .setTitle('In that example, what could the observer guess? (optional)');

  // Section D: trade-offs (Gap 3)
  form.addPageBreakItem().setTitle('Priorities and trade-offs');

  form.addCheckboxItem()
    .setTitle('Choose up to three things that matter most to you')
    .setChoiceValues([
      'Finding the right records or evidence',
      'Hiding my question from the hospitals',
      'Hiding which hospitals I searched',
      'Strict control over who can see which records',
      'Fast results',
      'Low network and storage cost',
      'Easy for a hospital to join',
    ])
    .setValidation(FormApp.createCheckboxValidation()
      .setHelpText('Please choose no more than three.')
      .requireSelectAtMost(3)
      .build());

  form.addMultipleChoiceItem()
    .setTitle('What is the longest you would wait for search results?')
    .setChoiceValues(['Under 2 seconds', '2 to 5 seconds', '5 to 15 seconds',
                      'More than 15 seconds', 'Depends on the task']);

  form.addGridItem()
    .setTitle('How much do you agree with each statement?')
    .setRows([
      'I would accept slightly less complete results if no hospital could see my question.',
      'I would accept extra network traffic if it hid which hospitals I searched.',
      'I would accept a one-time setup download (for example a few hundred MB) for better privacy.',
      'Names, dates and ID numbers must be removed from records before I see them.',
      'I should receive only the records I need, even if searching is slower.',
    ])
    .setColumns(AGREE_5);

  // Section E: access and trust
  form.addPageBreakItem().setTitle('Access and trust');

  form.addMultipleChoiceItem()
    .setTitle('Who should decide who can see a hospital\'s records?')
    .setChoiceValues([
      'The hospital that holds the records',
      'A central authority for the group of hospitals',
      'The patient, through consent',
      'A combination of these',
      'Not sure',
    ]);

  form.addCheckboxItem()
    .setTitle('What would increase your trust in such a system? (select all that apply)')
    .setChoiceValues([
      'Open-source code',
      'A log of every request made to each hospital',
      'A view of exactly what left my device',
      'An independent security review',
      'Run by my own institution',
      'Published test results',
    ])
    .showOtherOption(true);

  form.addMultipleChoiceItem()
    .setTitle('Where would you prefer the search software to run?')
    .setChoiceValues(['On my own device', 'On my institution\'s server',
                      'On a shared cloud service', 'No preference']);

  // Section F: open questions
  form.addPageBreakItem().setTitle('Final questions');

  form.addParagraphTextItem()
    .setTitle('What would stop you from using a system like this? (optional)');

  form.addParagraphTextItem()
    .setTitle('Is there anything important we have not asked about? (optional)');

  // Responses go to a new sheet in your Drive.
  var sheet = SpreadsheetApp.create('Requirements survey responses');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());

  Logger.log('Edit the form:      ' + form.getEditUrl());
  Logger.log('Respondent link:    ' + form.getPublishedUrl() + '  (share only after ethics approval)');
  Logger.log('Response sheet:     ' + sheet.getUrl());
}
