"""
@module terms.terms_seed

Seed rows (upserted by name — never insert-by-name). Three boilerplate
TermsDocuments an operator edits, clones per app, or switches on:

  demo-terms       ACTIVE by default — the public-demonstration terms
                   (the same text the hub publishes at /docs/demo-terms.html)
  standard-terms   inactive template for an ordinary self-hosted instance
  privacy-notice   inactive template for a notice (no acceptance required)

None of this is legal advice; it is plain-language boilerplate with the
elements such documents usually carry. `version` is a date: bump it when
the text changes and every visitor is asked again.
"""
from terms.terms_basis import TermsDocument

TERMS_VERSION = '2026-09-09'

DEMO_TERMS_MD = """\
## What a demonstration instance is

A demonstration instance runs the same free and open-source software you can install yourself. It is operated so visitors can see what Polari does and click around. It is not a service, not an account provider, and not a place to store work. The people running it may reset it, change it, take it offline or delete everything on it at any time, without notice.

## Do not enter personal information

Do not put information about yourself or anyone else into a demonstration instance. That includes names, addresses, phone numbers, email addresses, photographs of people, health, financial, employment or legal details, identifiers of any kind, and anything else that could identify or describe a person. This applies to every field, upload, comment, note and file, and to information about other people just as much as about you.

If you entered something you should not have, tell the operator so it can be removed. Removal is best effort: because the instance can be copied, reset and republished, no promise is made that a deletion reaches every copy.

## Nothing here is private or kept

- Anything you enter may be visible to other visitors, may appear in exports and screenshots, and may be published as example data.
- Data is not backed up for you and may be wiped at any time. Do not rely on anything being there tomorrow.
- Operators and maintainers can see everything on the instance, including logs of what was done.

## Accounts and logins

Where a demonstration instance offers a login, treat it as a throwaway. Never reuse a password you use anywhere else. Accounts may be shared, reset or removed without notice. There is no account recovery.

## Acceptable use

Use the instance to explore the software. Do not use it to store, transmit or process information about other people, to run anything unlawful, to attack the instance or other systems, or to generate load beyond ordinary browsing. Operators may block access without notice.

## No warranty, no promises

The software is free and open source under the GNU General Public License, version 3, and the instance is provided as is. There is no warranty of any kind and no promise of availability, accuracy, security or fitness for any purpose. Nothing shown on a demonstration instance is advice of any kind. To the fullest extent permitted by law, the operators and contributors are not liable for any loss arising from its use.

## Running your own

If you want to keep your data, install Polari yourself: an isle is your own private network, and everything you enter there stays on your own hardware.

## Changes to these terms

These terms carry a version date. When it changes, the instance asks every visitor to read and acknowledge them again.
"""

STANDARD_TERMS_MD = """\
## The service

This instance of Polari is operated by the operator named below for the people it admits. Polari is free and open-source software (GNU General Public License, version 3); these terms cover the use of THIS instance, not the software, which you may run yourself under its licence.

## Your account and your data

You are responsible for what you enter and for keeping your login to yourself. The operator stores what you enter in order to run the instance for you; the operator does not sell it and does not hand it to anyone outside the instance except as the law requires or as you direct (for example, by exposing an app to another isle). You can ask the operator to export or delete your data.

## Acceptable use

Do not use the instance to break the law, to harm other people, to attack the instance or other systems, or to interfere with other members' use. The operator may suspend access that does this.

## Availability and changes

The operator will try to keep the instance running but does not promise uptime, and may change, migrate or retire it with reasonable notice. Backups are the operator's responsibility to the extent stated by the operator, not implied by these terms.

## No warranty and limitation of liability

The instance and the software are provided as is, without warranty of any kind. To the fullest extent permitted by law, the operator and the software's contributors are not liable for indirect or consequential loss arising from use of the instance.

## Contact and changes

Questions go to the contact named on this document. These terms carry a version date; when it changes, members are asked to accept the new version before continuing.
"""

PRIVACY_NOTICE_MD = """\
## What this instance collects

This instance keeps the data you enter into its apps, the account details its login server holds (name, email address, the roles you are given), and technical logs of requests (addresses and timestamps) for keeping it running securely.

## Why

To run the apps for you, to keep the instance secure, and to let the operator answer your requests. Nothing is used for advertising and nothing is sold.

## Who can see it

The operator and maintainers of this instance. Other members see what the apps' sharing settings expose to them. Apps exposed beyond the isle (archipelago, VPN, mesh, web) show what their exposure row says, and nothing more.

## How long

For as long as you are a member, then as long as the operator's backups keep it. You can ask for export or deletion at any time using the contact on this document.

## Your choices

You can decline to enter anything, ask what is held about you, and ask for it to be corrected or deleted.
"""

SEED_TERMS_DOCUMENTS = [
    {'name': 'demo-terms', 'title': 'Demo terms', 'kind': 'demo', 'scope': 'global', 'app_name': '',
     'version': TERMS_VERSION, 'active': True, 'requires_acceptance': True, 'show_bar': True,
     'bar_text': 'Demonstration instance. Do not enter personal information — anything you put here may be public and can be wiped at any time.',
     'summary': 'This is a public demonstration of Polari. It exists so you can try the software, not to hold anyone\'s data.',
     'body_md': DEMO_TERMS_MD, 'effective_at': TERMS_VERSION, 'contact': '',
     'notes': 'Seeded boilerplate for public demonstration instances. Plain language, not legal advice. Bump `version` when the text changes.'},
    {'name': 'standard-terms', 'title': 'Terms of use', 'kind': 'standard', 'scope': 'global', 'app_name': '',
     'version': TERMS_VERSION, 'active': False, 'requires_acceptance': True, 'show_bar': False, 'bar_text': '',
     'summary': 'The terms for members of this self-hosted instance.',
     'body_md': STANDARD_TERMS_MD, 'effective_at': TERMS_VERSION, 'contact': '',
     'notes': 'Template for an ordinary self-hosted instance: fill in `contact`, edit, set active. Not legal advice.'},
    {'name': 'privacy-notice', 'title': 'Privacy notice', 'kind': 'privacy', 'scope': 'global', 'app_name': '',
     'version': TERMS_VERSION, 'active': False, 'requires_acceptance': False, 'show_bar': False, 'bar_text': '',
     'summary': 'What this instance collects, why, who sees it, and for how long.',
     'body_md': PRIVACY_NOTICE_MD, 'effective_at': TERMS_VERSION, 'contact': '',
     'notes': 'Template notice (no acceptance required — shown, not gated). Not legal advice.'},
]

TERMS_SEED_PAIRS = [
    ('TermsDocument', TermsDocument, SEED_TERMS_DOCUMENTS),
]
