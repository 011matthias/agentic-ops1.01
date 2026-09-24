"""Dirk's curated Zoho expense accounts, per legal entity. GENERATED.

Do not edit by hand. Regenerate with:

    uv run tools/compile-brisken-gl-taxonomy.py --workbook <sheet> \\
        --revision <the sheet's save date> --expected-counts <org=n,...>

Source: CoA-expense-relevant-BCS-BTS-260923.xlsx, marked `Expense Relevant` by Dirk, saved 2026-09-23.

LEAVES maps an account CODE to (branch, {org_id: (account_id, name,
postable, reason)}). The code is the identity because it is stable across
the three orgs while the name is not: E100010-31 reads `Travel Expense |
Food` in BCS and BTS and `CorpServ | Travel Expense | Food` in CorpServ.
`account_id` is the numeric Zoho id and is the only thing that may reach a
payload; a NAME passed where an id was expected does not error, it posts
to a default. Non-postable rows are present WITH a reason so a refusal can
say which of four facts it hit rather than `unknown reference`.
"""

CURATED_REVISION = '2026-09-23'
SOURCE_WORKBOOK = 'CoA-expense-relevant-BCS-BTS-260923.xlsx'
SOURCE_SHA256 = '30956252ad68e8a05bdb5d726a2f720ba97b532f86870def82dbe28f6d6b1ce1'

# Also the rollout and rollback lever: an org absent here is simply not
# covered, and the chain refuses for it instead of guessing.
CURATED_ORG_IDS = (
    '697686691',  # BCS
    '808232536',  # BTS
    '822741658',  # CorpServ
)

ORG_TABS = {
    '697686691': 'BCS',
    '808232536': 'BTS',
    '822741658': 'CorpServ',
}

POSTABLE_COUNTS = {
    '697686691': 67,
    '808232536': 64,
    '822741658': 68,
}

LEAVES = {
    '6013': (
        (),
        {
            '697686691': ('2031056000016940001', 'Visa Card  6013', False, 'not_expense_relevant'),
        },
    ),
    '9693': (
        (),
        {
            '697686691': ('2031056000017742154', 'Chase Visa | 9693 | Cloud Expenses', False, 'not_expense_relevant'),
        },
    ),
    'A090-20-1000-0000': (
        (),
        {
            '697686691': ('2031056000009891109', 'Bank Clearing Account - all currencies', False, 'not_expense_relevant'),
        },
    ),
    'A090-30-1000-0000': (
        (),
        {
            '808232536': ('4036956000000076371', 'Bank Clearing Account - all currencies', False, 'not_expense_relevant'),
        },
    ),
    'A090-50-1000-0000': (
        (),
        {
            '822741658': ('4373186000000078383', 'Bank Clearing Account - all currencies', False, 'not_expense_relevant'),
        },
    ),
    'A095-20-1000-0000': (
        (),
        {
            '697686691': ('2031056000000000358', 'Undeposited Funds', False, 'not_expense_relevant'),
        },
    ),
    'A095-20-1000-0000Z': (
        (),
        {
            '697686691': ('2031056000000000361', 'ZZZ | Cash In Hand | DO NOT USE 2', False, 'not_expense_relevant'),
        },
    ),
    'A095-30-1000-0000': (
        (),
        {
            '808232536': ('4036956000000076101', 'Undeposited Funds', False, 'not_expense_relevant'),
        },
    ),
    'A095-50-1000-0000': (
        (),
        {
            '822741658': ('4373186000000078111', 'Undeposited Funds', False, 'not_expense_relevant'),
        },
    ),
    'A100-20-1100-1930': (
        (),
        {
            '697686691': ('2031056000015949071', 'CHASE SAVINGS - 1930', False, 'not_expense_relevant'),
        },
    ),
    'A100-20-1100-5267': (
        (),
        {
            '697686691': ('2031056000000104181', 'CHASE SAVINGS - 5267 CLOSED', False, 'not_expense_relevant'),
        },
    ),
    'A100-20-1100-7292': (
        (),
        {
            '697686691': ('2031056000000104175', 'CHASE Checking - 7292', False, 'not_expense_relevant'),
        },
    ),
    'A100-20-1200-1976': (
        (),
        {
            '697686691': ('2031056000000132001', 'WISE EUR - 1976', False, 'not_expense_relevant'),
        },
    ),
    'A100-20-1200-5181': (
        (),
        {
            '697686691': ('2031056000000129516', 'WISE GBP - 5181', False, 'not_expense_relevant'),
        },
    ),
    'A100-20-1200-5745': (
        (),
        {
            '697686691': ('2031056000000132005', 'WISE USD - 5745', False, 'not_expense_relevant'),
        },
    ),
    'A100-20-1300-1120': (
        (),
        {
            '697686691': ('2031056000015962169', 'EDWARD JONES CASH - 1120', False, 'not_expense_relevant'),
        },
    ),
    'A100-30-1100-6688': (
        (),
        {
            '808232536': ('4036956000000081045', 'CHASE Checking - 6688', False, 'not_expense_relevant'),
        },
    ),
    'A100-30-1200-1480GBP': (
        (),
        {
            '808232536': ('4036956000001081001', 'WISE GBP - 1480', False, 'not_expense_relevant'),
        },
    ),
    'A100-30-1200-1480ILS': (
        (),
        {
            '808232536': ('4036956000001587045', 'Wise - ILS - 1480', False, 'not_expense_relevant'),
        },
    ),
    'A100-30-1200-7742': (
        (),
        {
            '808232536': ('4036956000000083019', 'WISE EUR - 7742', False, 'not_expense_relevant'),
        },
    ),
    'A100-30-1200-9786': (
        (),
        {
            '808232536': ('4036956000000083027', 'WISE USD - 9786', False, 'not_expense_relevant'),
        },
    ),
    'A100-30-1300-1277': (
        (),
        {
            '808232536': ('4036956000000428918', 'EDWARD JONES CASH - 1277', False, 'not_expense_relevant'),
        },
    ),
    'A100-50-1100-9388': (
        (),
        {
            '822741658': ('4373186000000079891', 'CHASE Checking - 9388', False, 'not_expense_relevant'),
        },
    ),
    'A100-50-1200-0179': (
        (),
        {
            '822741658': ('4373186000000079906', 'WISE EUR - 0179', False, 'not_expense_relevant'),
        },
    ),
    'A100-50-1200-9197': (
        (),
        {
            '822741658': ('4373186000000079901', 'WISE USD - 9197', False, 'not_expense_relevant'),
        },
    ),
    'A100-50-1300-1209': (
        (),
        {
            '822741658': ('4373186000000079896', 'EDWARD JONES CASH - 1209', False, 'not_expense_relevant'),
        },
    ),
    'A180-20-6000-0000': (
        (),
        {
            '697686691': ('2031056000000609151', 'N/R - share holders', False, 'not_expense_relevant'),
        },
    ),
    'A180-20-6010-DN00': (
        (),
        {
            '697686691': ('2031056000000609173', 'N/R - Dirk Neumann I/O', False, 'not_expense_relevant'),
        },
    ),
    'A180-20-6010-DN01Z': (
        (),
        {
            '697686691': ('2031056000000104597', 'N/P - Dirk Neumann OBSOLETE', False, 'not_expense_relevant'),
        },
    ),
    'A180-20-6020-JB00': (
        (),
        {
            '697686691': ('2031056000000609193', 'N/R - Juliano Brugnago', False, 'not_expense_relevant'),
        },
    ),
    'A180-20-7000-0000': (
        (),
        {
            '697686691': ('2031056000013905173', 'N/R - employees', False, 'not_expense_relevant'),
        },
    ),
    'A180-20-7010-DN00': (
        (),
        {
            '697686691': ('2031056000013905179', 'N/R - Dirk Neumann I/O Employee', False, 'not_expense_relevant'),
        },
    ),
    'A180-20-8000-0000': (
        (),
        {
            '697686691': ('2031056000015215113', 'N/R - Related Companies', False, 'not_expense_relevant'),
        },
    ),
    'A180-20-8100-HOLD': (
        (),
        {
            '697686691': ('2031056000015215120', 'N/R - BRISKEN HOLDING', False, 'not_expense_relevant'),
        },
    ),
    'A180-20-8200-CSER': (
        (),
        {
            '697686691': ('2031056000015215127', 'N/R - BRISKEN CLOUD SERVICES', False, 'not_expense_relevant'),
        },
    ),
    'A180-20-8300-CONS': (
        (),
        {
            '697686691': ('2031056000015215134', 'N/R - BRISKEN CONSULTING', False, 'not_expense_relevant'),
        },
    ),
    'A180-20-8400-CSOL': (
        (),
        {
            '697686691': ('2031056000015215141', 'N/R - BRISKEN CLOUD SOLUTIONS', False, 'not_expense_relevant'),
        },
    ),
    'A180-20-8500-CORP': (
        (),
        {
            '697686691': ('2031056000015319701', 'N/R - BRISKEN CORP SERVICES', False, 'not_expense_relevant'),
        },
    ),
    'A180-20-8600-GMBH': (
        (),
        {
            '697686691': ('2031056000015215148', 'N/R - BRISKEN GMBH', False, 'not_expense_relevant'),
        },
    ),
    'A180-30-6000-0000': (
        (),
        {
            '808232536': ('4036956000000076247', 'N/R - share holders', False, 'not_expense_relevant'),
        },
    ),
    'A180-30-6010-DN00': (
        (),
        {
            '808232536': ('4036956000000076249', 'N/R - Dirk Neumann I/O', False, 'not_expense_relevant'),
        },
    ),
    'A180-30-6020-JB00': (
        (),
        {
            '808232536': ('4036956000000076251', 'N/R - Juliano Brugnago', False, 'not_expense_relevant'),
        },
    ),
    'A180-30-7000-0000': (
        (),
        {
            '808232536': ('4036956000000076391', 'N/R - employees', False, 'not_expense_relevant'),
        },
    ),
    'A180-30-7010-DN00': (
        (),
        {
            '808232536': ('4036956000000076393', 'N/R - Dirk Neumann I/O Employee', False, 'not_expense_relevant'),
        },
    ),
    'A180-30-8000-0000': (
        (),
        {
            '808232536': ('4036956000000258087', 'N/R - Related Companies', False, 'not_expense_relevant'),
        },
    ),
    'A180-30-8100-HOLD': (
        (),
        {
            '808232536': ('4036956000000258094', 'N/R - BRISKEN HOLDING', False, 'not_expense_relevant'),
        },
    ),
    'A180-30-8200-CSER': (
        (),
        {
            '808232536': ('4036956000000258101', 'N/R - BRISKEN CLOUD SERVICES', False, 'not_expense_relevant'),
        },
    ),
    'A180-30-8300-CONS': (
        (),
        {
            '808232536': ('4036956000000258108', 'N/R - BRISKEN CONSULTING', False, 'not_expense_relevant'),
        },
    ),
    'A180-30-8400-CSOL': (
        (),
        {
            '808232536': ('4036956000000258115', 'N/R - BRISKEN CLOUD SOLUTIONS', False, 'not_expense_relevant'),
        },
    ),
    'A180-30-8500-CORP': (
        (),
        {
            '808232536': ('4036956000000286637', 'N/R - BRISKEN CORP SERVICES', False, 'not_expense_relevant'),
        },
    ),
    'A180-30-8600-GMBH': (
        (),
        {
            '808232536': ('4036956000000258122', 'N/R - BRISKEN GMBH', False, 'not_expense_relevant'),
        },
    ),
    'A180-50-6000-0000': (
        (),
        {
            '822741658': ('4373186000000078259', 'N/R - share holders', False, 'not_expense_relevant'),
        },
    ),
    'A180-50-6010-DN00': (
        (),
        {
            '822741658': ('4373186000000078261', 'N/R - Dirk Neumann - clearing until 2024', False, 'not_expense_relevant'),
        },
    ),
    'A180-50-6020-PN001': (
        (),
        {
            '822741658': ('4373186000000078263', 'N/R - PN001 - Multi Purpose Loan 2023', False, 'not_expense_relevant'),
        },
    ),
    'A180-50-7000-0000': (
        (),
        {
            '822741658': ('4373186000000078403', 'N/R - Dirk Neumann I/O Ongoing', False, 'not_expense_relevant'),
        },
    ),
    'A180-50-7010-PN002': (
        (),
        {
            '822741658': ('4373186000000078405', 'N/R - PN002-RealEstateRef 2025', False, 'not_expense_relevant'),
        },
    ),
    'A180-50-8000-0000': (
        (),
        {
            '822741658': ('4373186000000078449', 'N/R - Related Companies', False, 'not_expense_relevant'),
        },
    ),
    'A180-50-8100-HOLD': (
        (),
        {
            '822741658': ('4373186000000078451', 'N/R - BRISKEN HOLDING', False, 'not_expense_relevant'),
        },
    ),
    'A180-50-8200-CSER': (
        (),
        {
            '822741658': ('4373186000000078453', 'N/R - BRISKEN CLOUD SERVICES', False, 'not_expense_relevant'),
        },
    ),
    'A180-50-8300-CONS': (
        (),
        {
            '822741658': ('4373186000000078455', 'N/R - BRISKEN CONSULTING', False, 'not_expense_relevant'),
        },
    ),
    'A180-50-8400-CSOL': (
        (),
        {
            '822741658': ('4373186000000078457', 'N/R - BRISKEN CLOUD SOLUTIONS', False, 'not_expense_relevant'),
        },
    ),
    'A180-50-8500-CORP': (
        (),
        {
            '822741658': ('4373186000000078475', 'N/R - BRISKEN CORP SERVICES', False, 'not_expense_relevant'),
        },
    ),
    'A180-50-8600-GMBH': (
        (),
        {
            '822741658': ('4373186000000078459', 'N/R - BRISKEN GMBH', False, 'not_expense_relevant'),
        },
    ),
    'A200-20-0001-HOLD': (
        (),
        {
            '697686691': ('2031056000016064057', 'BRISKEN IN HOUSE BANK - HOLDING', False, 'not_expense_relevant'),
        },
    ),
    'A200-30-0001-HOLD': (
        (),
        {
            '808232536': ('4036956000000462001', 'BRISKEN IN HOUSE BANK - HOLDING', False, 'not_expense_relevant'),
        },
    ),
    'A200-50-0001-HOLD': (
        (),
        {
            '822741658': ('4373186000000089027', 'BRISKEN IN HOUSE BANK - HOLDING', False, 'not_expense_relevant'),
        },
    ),
    'A200040': (
        (),
        {
            '697686691': ('2031056000000104211', 'Organization Costs', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076137', 'Organization Costs', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078149', 'Organization Costs', False, 'not_expense_relevant'),
        },
    ),
    'A300000': (
        (),
        {
            '697686691': ('2031056000000000364', 'Accounts Receivable', False, 'not_expense_relevant'),
            '808232536': ('4036956000000000364', 'Accounts Receivable', False, 'not_expense_relevant'),
            '822741658': ('4373186000000000364', 'Accounts Receivable', False, 'not_expense_relevant'),
        },
    ),
    'A300020': (
        (),
        {
            '697686691': ('2031056000017696023', 'Intangible Assets', False, 'not_expense_relevant'),
            '808232536': ('4036956000001028001', 'Intangible Assets', False, 'not_expense_relevant'),
            '822741658': ('4373186000000232376', 'Intangible Assets', False, 'not_expense_relevant'),
        },
    ),
    'A30002010': (
        (),
        {
            '697686691': ('2031056000017696030', 'Software', False, 'not_expense_relevant'),
            '808232536': ('4036956000001028017', 'Software', False, 'not_expense_relevant'),
            '822741658': ('4373186000000232396', 'Software', False, 'not_expense_relevant'),
        },
    ),
    'A3000201010': (
        (),
        {
            '697686691': ('2031056000017696037', 'Software - Externally Acquired', False, 'not_expense_relevant'),
            '808232536': ('4036956000001028024', 'Software - Externally Acquired', False, 'not_expense_relevant'),
            '822741658': ('4373186000000232403', 'Software - Externally acquired', False, 'not_expense_relevant'),
        },
    ),
    'A300020101010': (
        (),
        {
            '697686691': ('2031056000000104195', 'Database Software', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076135', 'Database Software', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078147', 'Database Software', False, 'not_expense_relevant'),
        },
    ),
    'A3000201020': (
        (),
        {
            '697686691': ('2031056000017696044', 'Software - Internal R&D', False, 'not_expense_relevant'),
            '808232536': ('4036956000001028031', 'Software - Internal R&D', False, 'not_expense_relevant'),
            '822741658': ('4373186000000232410', 'Software - Internal R&D', False, 'not_expense_relevant'),
        },
    ),
    'A300020102010': (
        (),
        {
            '697686691': ('2031056000017696055', 'Software Internal R&D - Domestic', False, 'not_expense_relevant'),
            '808232536': ('4036956000001028038', 'Software Internal R&D - Domestic', False, 'not_expense_relevant'),
            '822741658': ('4373186000000232423', 'Software Internal R&D - Domestic', False, 'not_expense_relevant'),
        },
    ),
    'A300020102020': (
        (),
        {
            '697686691': ('2031056000017696066', 'Software Internal R&D - International', False, 'not_expense_relevant'),
            '808232536': ('4036956000001028045', 'Software Internal R&D - International', False, 'not_expense_relevant'),
            '822741658': ('4373186000000232430', 'Software Internal R&D - International', False, 'not_expense_relevant'),
        },
    ),
    'A30002090': (
        (),
        {
            '697686691': ('2031056000000104221', 'Accumulated Amortization', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076139', 'Accumulated Amortization', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078151', 'Accumulated Amortization', False, 'not_expense_relevant'),
        },
    ),
    'A3000209010': (
        (),
        {
            '697686691': ('2031056000017696077', 'Accumulated Amortization - Software', False, 'not_expense_relevant'),
            '808232536': ('4036956000001028010', 'Accumulated Amortization - Software', False, 'not_expense_relevant'),
            '822741658': ('4373186000000232389', 'Accummulated Amortization - Software', False, 'not_expense_relevant'),
        },
    ),
    'A300030': (
        (),
        {
            '697686691': ('2031056000017696001', 'Property, Plant & Equipment', False, 'not_expense_relevant'),
            '808232536': ('4036956000001028060', 'Property, Plant & Equipment', False, 'not_expense_relevant'),
            '822741658': ('4373186000000232351', 'Property, Plant & Equipments', False, 'not_expense_relevant'),
        },
    ),
    'A30003010': (
        (),
        {
            '697686691': ('2031056000000104203', 'Furniture', False, 'not_expense_relevant'),
            '808232536': ('4036956000000000367', 'Furniture', False, 'not_expense_relevant'),
            '822741658': ('4373186000000000367', 'Furniture and Equipment', False, 'not_expense_relevant'),
        },
    ),
    'A30003020': (
        (),
        {
            '697686691': ('2031056000000104187', 'Computer Equipment', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076133', 'Computer Equipment', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078145', 'Computer Equipment', False, 'not_expense_relevant'),
        },
    ),
    'A30003030': (
        (),
        {
            '697686691': ('2031056000017737021', 'Machinary and Other Equipments', False, 'not_expense_relevant'),
            '808232536': ('4036956000001028081', 'Machinary and Other Equipments', False, 'not_expense_relevant'),
        },
    ),
    'A30003090': (
        (),
        {
            '697686691': ('2031056000000104229', 'Accumulated Depreciation', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076141', 'Accumulated Depreciation', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078153', 'Accumulated Depreciation', False, 'not_expense_relevant'),
        },
    ),
    'A500100Z': (
        (),
        {
            '808232536': ('4036956000000000370', 'Advance Tax', False, 'not_expense_relevant'),
        },
    ),
    'A500200Z': (
        (),
        {
            '808232536': ('4036956000000035001', 'Employee Advance', False, 'not_expense_relevant'),
        },
    ),
    'A500300': (
        (),
        {
            '697686691': ('2031056000000068010', 'Prepaid Expenses', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076012', 'Prepaid Expenses', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078012', 'Prepaid Expenses', False, 'not_expense_relevant'),
        },
    ),
    'A500400Z': (
        (),
        {
            '808232536': ('4036956000000076127', 'Inventory Asset (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'E000010': (
        (),
        {
            '697686691': ('2031056000033061222', 'R&D', True, ''),
        },
    ),
    'E000010-91': (
        (),
        {
            '697686691': ('2031056000020487003', 'Software Domestic R&D - IC Contractors', False, 'not_expense_relevant'),
        },
    ),
    'E000010-92': (
        (),
        {
            '697686691': ('2031056000020487010', 'Software Domestic R&D - 3rd Party Contractors', False, 'not_expense_relevant'),
        },
    ),
    'E000010-96': (
        (),
        {
            '697686691': ('2031056000020487017', 'Software International R&D - IC Contractors', False, 'not_expense_relevant'),
        },
    ),
    'E000010-97': (
        (),
        {
            '697686691': ('2031056000020487026', 'Software International R&D - 3rd Party Contractors', False, 'not_expense_relevant'),
        },
    ),
    'E100000': (
        (),
        {
            '822741658': ('4373186000000908591', 'CorpServ | OpeEx', True, ''),
        },
    ),
    'E100010': (
        ('OpeEx',),
        {
            '697686691': ('2031056000000000418', 'Travel Expense', True, ''),
            '808232536': ('4036956000000000418', 'Travel Expense', True, ''),
            '822741658': ('4373186000000000418', 'CorpServ | Travel Expenses', True, ''),
        },
    ),
    'E100010-01': (
        ('Travel Expense',),
        {
            '697686691': ('2031056000000000424', 'Travel Expense | Transportation', True, ''),
            '808232536': ('4036956000000076119', 'Travel Expense | Transportation', True, ''),
            '822741658': ('4373186000000078129', 'CorpServ |Travel Expense | Transportation', True, ''),
        },
    ),
    'E100010-06': (
        ('Travel Expense',),
        {
            '697686691': ('2031056000000079007', 'Travel Expense: Parking & Tolls', True, ''),
            '808232536': ('4036956000000076129', 'Travel Expense: Parking & Tolls', True, ''),
            '822741658': ('4373186000000078141', 'CorpServ | Travel Expense | Parking & Tolls', True, ''),
        },
    ),
    'E100010-11': (
        ('Travel Expense',),
        {
            '697686691': ('2031056000000101696', 'Travel Expense: Per diem', True, ''),
            '808232536': ('4036956000000076131', 'Travel Expense: Per diem', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078143', 'Travel Expense: Per diem', False, 'not_expense_relevant'),
        },
    ),
    'E100010-16': (
        (),
        {
            '697686691': ('2031056000000106623', 'Travel Expense: Public Transport', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076227', 'Travel Expense: Public Transport', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078239', 'Travel Expense: Public Transport', False, 'not_expense_relevant'),
        },
    ),
    'E100010-21': (
        (),
        {
            '697686691': ('2031056000000104247', 'Travel Expense:Flights', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076143', 'Travel Expense:Flights', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078155', 'Travel Expense:Flights', False, 'not_expense_relevant'),
        },
    ),
    'E100010-26': (
        ('Travel Expense',),
        {
            '697686691': ('2031056000000104255', 'Travel Expense | Accommodation', True, ''),
            '808232536': ('4036956000000076145', 'Travel Expense | Accommodation', True, ''),
            '822741658': ('4373186000000078157', 'CorpServ | Travel Expense | Accommodation', True, ''),
        },
    ),
    'E100010-31': (
        ('Travel Expense',),
        {
            '697686691': ('2031056000000104265', 'Travel Expense | Food', True, ''),
            '808232536': ('4036956000000076147', 'Travel Expense | Food', True, ''),
            '822741658': ('4373186000000078159', 'CorpServ | Travel Expense | Food', True, ''),
        },
    ),
    'E100010-36': (
        (),
        {
            '697686691': ('2031056000000104273', 'Travel Expense:Rental Cars', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076149', 'Travel Expense:Rental Cars', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078161', 'Travel Expense:Rental Cars', False, 'not_expense_relevant'),
        },
    ),
    'E100010-41': (
        (),
        {
            '697686691': ('2031056000000104281', 'Travel Expense:Taxi/Uber', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076151', 'Travel Expense:Taxi/Uber', False, 'not_expense_relevant'),
        },
    ),
    'E100020': (
        ('OpeEx',),
        {
            '822741658': ('4373186000000812017', 'CorpServ | Business Expenses', True, ''),
        },
    ),
    'E100020-10': (
        ('OpeEx', 'Business Expenses'),
        {
            '822741658': ('4373186000000812042', 'CorpServ | IT Expenses', True, ''),
        },
    ),
    'E100020-20': (
        ('OpeEx', 'Business Expenses'),
        {
            '822741658': ('4373186000000835009', 'CorpServ| Support Administration', True, ''),
        },
    ),
    'E100020-30': (
        ('OpeEx', 'Business Expenses'),
        {
            '822741658': ('4373186000000835026', 'CorpServ| Technical and Business Consulting', True, ''),
        },
    ),
    'E100020-41': (
        ('OpeEx', 'Business Expenses'),
        {
            '822741658': ('4373186000000078163', 'CorpServ | Professional Services Fee', True, ''),
        },
    ),
    'E100020-80': (
        ('OpeEx', 'Business Expenses'),
        {
            '822741658': ('4373186000000078165', 'CorpServ | Misc Expense', True, ''),
        },
    ),
    'E100020-90': (
        ('OpeEx', 'Business Expenses'),
        {
            '822741658': ('4373186000000078167', 'CorpServ | Computer Equipment to be depreciated', True, ''),
        },
    ),
    'E100090': (
        (),
        {
            '697686691': ('2031056000000000448', 'Meals and Entertainment', False, 'not_expense_relevant'),
            '808232536': ('4036956000000000448', 'Meals and Entertainment', False, 'not_expense_relevant'),
            '822741658': ('4373186000000000448', 'Meals and Entertainment', False, 'not_expense_relevant'),
        },
    ),
    'E200020': (
        (),
        {
            '697686691': ('2031056000000104305', 'Computer expenses depreciated', True, ''),
            '808232536': ('4036956000000076155', 'Computer expenses depreciated', False, 'not_expense_relevant'),
        },
    ),
    'E200060': (
        (),
        {
            '697686691': ('2031056000000104313', 'Depreciation Expense', False, 'not_expense_relevant'),
            '808232536': ('4036956000000000451', 'Depreciation Expense', False, 'not_expense_relevant'),
            '822741658': ('4373186000000000451', 'Depreciation Expense', False, 'not_expense_relevant'),
        },
    ),
    'E300000': (
        (),
        {
            '697686691': ('2031056000000104329', 'Payroll expenses', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076159', 'Payroll expenses', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078171', 'CorpServ | Payroll expenses', False, 'not_expense_relevant'),
        },
    ),
    'E300000-05': (
        (),
        {
            '697686691': ('2031056000000104337', 'Payroll Taxes: Federal Income Tax', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076161', 'Payroll Taxes: Federal Income Tax', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078173', 'CorpServ | Payroll Taxes: Federal Income Tax', False, 'not_expense_relevant'),
        },
    ),
    'E300000-10': (
        (),
        {
            '697686691': ('2031056000000403080', 'Payroll Taxes: Medicare', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076237', 'Payroll Taxes: Medicare', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078249', 'CorpServ | Payroll Taxes: Medicare', False, 'not_expense_relevant'),
        },
    ),
    'E300000-20': (
        (),
        {
            '697686691': ('2031056000000403098', 'Payroll Taxes: Social Security', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076239', 'Payroll Taxes: Social Security', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078251', 'CorpServ | Payroll Taxes: Social Security', False, 'not_expense_relevant'),
        },
    ),
    'E300000-30': (
        (),
        {
            '697686691': ('2031056000000403190', 'Payroll Taxes: Texas Workforce', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076241', 'Payroll Taxes: Texas Workforce', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078253', 'CorpServ | Payroll Taxes: Texas Workforce', False, 'not_expense_relevant'),
        },
    ),
    'E300000-40': (
        (),
        {
            '697686691': ('2031056000009294021', 'Payroll Tax - Federal Unemployment', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076369', 'Payroll Taxes: Federal Unemployment', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078381', 'CorpServ | Payroll Tax - Federal Unemployment', False, 'not_expense_relevant'),
        },
    ),
    'E300000-45': (
        (),
        {
            '697686691': ('2031056000001429007', 'Payroll Expenses: Salaries', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076265', 'Payroll Expenses: Salaries', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078277', 'CorpServ | Payroll Expenses: Salaries', False, 'not_expense_relevant'),
        },
    ),
    'E300000-50': (
        (),
        {
            '697686691': ('2031056000000104347', 'Payroll Expenses: SEP IRA', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076163', 'Payroll Expenses: SEP IRA', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078175', 'CorpServ | Payroll Expenses: SEP IRA', False, 'not_expense_relevant'),
        },
    ),
    'E300000-60': (
        ('Payroll expenses',),
        {
            '697686691': ('2031056000000104481', 'Payroll Expenses: Payroll Service', True, ''),
            '808232536': ('4036956000000076189', 'Payroll Expenses: Payroll Service', True, ''),
            '822741658': ('4373186000000078201', 'CorpServ | Payroll Expenses: Payroll Service', True, ''),
        },
    ),
    'E300000-70': (
        ('Payroll expenses',),
        {
            '697686691': ('2031056000000104321', 'Payroll Expense: Continuing Education', True, ''),
            '808232536': ('4036956000000076157', 'Payroll Expense: Continuing Education', True, ''),
            '822741658': ('4373186000000078169', 'CorpServ | Payroll Expense: Continuing Education', True, ''),
        },
    ),
    'E300040': (
        (),
        {
            '697686691': ('2031056000000000445', 'Salaries and Employee Wages', False, 'not_expense_relevant'),
            '808232536': ('4036956000000000445', 'Salaries and Employee Wages', False, 'not_expense_relevant'),
            '822741658': ('4373186000000000445', 'Salaries and Employee Wages', False, 'not_expense_relevant'),
        },
    ),
    'E400010': (
        (),
        {
            '697686691': ('2031056000000000439', 'Bad Debt', False, 'not_expense_relevant'),
            '808232536': ('4036956000000000439', 'Bad Debt', False, 'not_expense_relevant'),
            '822741658': ('4373186000000000439', 'Bad Debt', False, 'not_expense_relevant'),
        },
    ),
    'E400020': (
        (),
        {
            '697686691': ('2031056000000000409', 'Bank Fees and Charges', True, ''),
            '808232536': ('4036956000000000409', 'Bank Fees and Charges', True, ''),
            '822741658': ('4373186000000000409', 'Bank Fees and Charges', True, ''),
        },
    ),
    'E400060': (
        (),
        {
            '697686691': ('2031056000000104383', 'Reconciliation Discrepancies', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076171', 'Reconciliation Discrepancies', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078183', 'Reconciliation Discrepancies', False, 'not_expense_relevant'),
        },
    ),
    'E500000': (
        (),
        {
            '822741658': ('4373186000000908600', 'MS | OpeEx', True, ''),
        },
    ),
    'E500010': (
        ('MS | OpeEx',),
        {
            '697686691': ('2031056000000104391', 'IT: Computer and Internet Expenses', True, ''),
            '808232536': ('4036956000000076173', 'IT: Computer and Internet Expenses', True, ''),
            '822741658': ('4373186000000078185', 'IT: Computer and Internet Expenses', True, ''),
        },
    ),
    'E500010-10': (
        ('IT: Computer and Internet Expenses',),
        {
            '697686691': ('2031056000007495755', 'IT: Cloud Subscriptions-ZOHO ERP', True, ''),
            '808232536': ('4036956000000076335', 'IT: Cloud Subscriptions-ZOHO ERP', True, ''),
            '822741658': ('4373186000000078347', 'IT: Cloud Subscriptions-ZOHO ERP', True, ''),
        },
    ),
    'E500010-20': (
        ('IT: Computer and Internet Expenses',),
        {
            '697686691': ('2031056000001808001', 'IT: Cloud Subscriptions-Microsoft office', True, ''),
            '808232536': ('4036956000000076285', 'IT: Cloud Subscriptions-Microsoft office', True, ''),
            '822741658': ('4373186000000078297', 'IT: Cloud Subscriptions-Microsoft office', True, ''),
        },
    ),
    'E500010-30': (
        ('IT: Computer and Internet Expenses',),
        {
            '697686691': ('2031056000000106807', 'IT: Cloud Subscriptions-Others', True, ''),
            '808232536': ('4036956000000076229', 'IT: Cloud Subscriptions-Others', True, ''),
            '822741658': ('4373186000000078241', 'IT: Cloud Subscriptions-Others', True, ''),
        },
    ),
    'E500010-40': (
        ('IT: Computer and Internet Expenses',),
        {
            '697686691': ('2031056000010326003', 'IT: equipment, peripherals, phones, devices', True, ''),
            '808232536': ('4036956000000076373', 'IT: equipment, peripherals, phones, devices', True, ''),
            '822741658': ('4373186000000078385', 'IT: equipment, peripherals, phones, devices', True, ''),
        },
    ),
    'E500020Z': (
        (),
        {
            '822741658': ('4373186000000078187', 'Dues and Subscriptions (NO LONGER USED)', False, 'not_expense_relevant'),
        },
    ),
    'E500030': (
        ('MS | OpeEx',),
        {
            '697686691': ('2031056000007495941', 'Office Infra and Admin', True, ''),
            '808232536': ('4036956000000076343', 'Office Infra and Admin', True, ''),
            '822741658': ('4373186000000078355', 'Office Infra and Admin', True, ''),
        },
    ),
    'E500030-10': (
        ('Office Infra and Admin',),
        {
            '697686691': ('2031056000000104423', 'Rent Expense', True, ''),
            '808232536': ('4036956000000000430', 'Rent Expense', True, ''),
            '822741658': ('4373186000000000430', 'Rent Expense', True, ''),
        },
    ),
    'E500030-20': (
        ('Office Infra and Admin',),
        {
            '697686691': ('2031056000000104407', 'Office Supplies', True, ''),
            '808232536': ('4036956000000000400', 'Office Supplies', True, ''),
            '822741658': ('4373186000000000400', 'Office Supplies', True, ''),
        },
    ),
    'E500030-30': (
        ('Office Infra and Admin',),
        {
            '697686691': ('2031056000000104415', 'Postage and Delivery', True, ''),
            '808232536': ('4036956000000076177', 'Postage and Delivery', True, ''),
            '822741658': ('4373186000000078189', 'Postage and Delivery', True, ''),
        },
    ),
    'E500030-40': (
        ('Office Infra and Admin',),
        {
            '697686691': ('2031056000000104431', 'Repairs and Maintenance', True, ''),
            '808232536': ('4036956000000000457', 'Repairs and Maintenance', True, ''),
            '822741658': ('4373186000000000457', 'Repairs and Maintenance', True, ''),
        },
    ),
    'E500030-50': (
        ('Office Infra and Admin',),
        {
            '697686691': ('2031056000000000421', 'Telephone Expense', True, ''),
            '808232536': ('4036956000000000421', 'Telephone Expense', True, ''),
            '822741658': ('4373186000000000421', 'Telephone Expense', True, ''),
        },
    ),
    'E500030-60': (
        ('Office Infra and Admin',),
        {
            '697686691': ('2031056000000104441', 'Utilities', True, ''),
            '808232536': ('4036956000000076179', 'Utilities', True, ''),
            '822741658': ('4373186000000078191', 'Utilities', True, ''),
        },
    ),
    'E600010': (
        ('MS | OpeEx',),
        {
            '697686691': ('2031056000001432067', 'Marketing & Selling Expenses', True, ''),
            '808232536': ('4036956000000076275', 'Marketing & Selling Expenses', True, ''),
            '822741658': ('4373186000000078287', 'Marketing & Selling Expenses', True, ''),
        },
    ),
    'E600010-04': (
        (),
        {
            '697686691': ('2031056000017982001', 'Sales Services', False, 'not_expense_relevant'),
            '808232536': ('4036956000001125039', 'Sales Services', False, 'not_expense_relevant'),
            '822741658': ('4373186000000278001', 'Sales Services', False, 'not_expense_relevant'),
        },
    ),
    'E600010-04-05': (
        (),
        {
            '697686691': ('2031056000020914013', 'Sales Services - payroll (Contractors)', False, 'not_expense_relevant'),
            '808232536': ('4036956000001818001', 'Sales Services - payroll (Contractors)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000580003', 'Sales Services - payroll (Contractors)', False, 'not_expense_relevant'),
        },
    ),
    'E600010-04-05-15': (
        (),
        {
            '697686691': ('2031056000022650219', 'Sales Services - 3rd Parties (Vendors)', False, 'not_expense_relevant'),
        },
    ),
    'E600010-04-10': (
        (),
        {
            '697686691': ('2031056000020914020', 'Sales Services - bonus/variable payroll (Contractors)', False, 'not_expense_relevant'),
            '808232536': ('4036956000001818008', 'Sales Services - bonus/variable payroll (Contractors)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000580010', 'Sales Services - bonus/variable payroll (Contractors)', False, 'not_expense_relevant'),
        },
    ),
    'E600010-04-15': (
        (),
        {
            '808232536': ('4036956000001913017', 'Sales Services - 3rd Parties (Vendors)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000580017', 'Sales Services - 3rd Parties (Vendors)', False, 'not_expense_relevant'),
        },
    ),
    'E600010-04-20': (
        (),
        {
            '697686691': ('2031056000020914027', 'Sales Services - bonus/variable (3rd Party)', False, 'not_expense_relevant'),
            '808232536': ('4036956000001818015', 'Sales Services - bonus/variable (3rd Party)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000580024', 'Sales Services - bonus/variable (3r Party)', False, 'not_expense_relevant'),
        },
    ),
    'E600010-04-30': (
        (),
        {
            '697686691': ('2031056000020914048', 'Sales Services - bonus/variable (IC Contractors)', False, 'not_expense_relevant'),
            '808232536': ('4036956000001818034', 'Sales Services - bonus/variable (IC Contractors)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000580286', 'Sales Services - bonus/variable (IC Contractors)', False, 'not_expense_relevant'),
        },
    ),
    'E600010-05': (
        ('Marketing & Selling Expenses',),
        {
            '697686691': ('2031056000000104449', 'Advertising and Promotion', True, ''),
            '808232536': ('4036956000000076181', 'Advertising and Promotion', True, ''),
            '822741658': ('4373186000000078193', 'Advertising and Promotion', True, ''),
        },
    ),
    'E600010-05-02': (
        ('Marketing & Selling Expenses', 'Advertising and Promotion'),
        {
            '697686691': ('2031056000007495091', 'LinkedIn Ads', True, ''),
            '808232536': ('4036956000000076325', 'LinkedIn Ads', True, ''),
            '822741658': ('4373186000000078337', 'LinkedIn Ads', True, ''),
        },
    ),
    'E600010-05-03': (
        ('Marketing & Selling Expenses', 'Advertising and Promotion'),
        {
            '697686691': ('2031056000009205022', 'Meta Ads', True, ''),
            '808232536': ('4036956000000076367', 'Meta Ads', True, ''),
            '822741658': ('4373186000000078379', 'Meta Ads', True, ''),
        },
    ),
    'E600010-05-05': (
        ('Marketing & Selling Expenses', 'Advertising and Promotion'),
        {
            '697686691': ('2031056000007495097', 'Google Ads', True, ''),
            '808232536': ('4036956000000076327', 'Google Ads', True, ''),
            '822741658': ('4373186000000078339', 'Google Ads', True, ''),
        },
    ),
    'E600010-05-06': (
        ('Marketing & Selling Expenses', 'Advertising and Promotion'),
        {
            '697686691': ('2031056000007495103', 'Other Online Ads', True, ''),
            '808232536': ('4036956000000076329', 'Other Online Ads', True, ''),
            '822741658': ('4373186000000078341', 'Other Online Advertising', True, ''),
        },
    ),
    'E600010-05-09': (
        ('Marketing & Selling Expenses', 'Advertising and Promotion'),
        {
            '697686691': ('2031056000007495109', 'Other Advertising and Promotions Expenses', True, ''),
            '822741658': ('4373186000000078343', 'Other Advertising and Promotions Expenses', True, ''),
        },
    ),
    'E600010-05-30': (
        ('Marketing & Selling Expenses', 'Advertising and Promotion'),
        {
            '697686691': ('2031056000004221009', 'SAP AppStore', True, ''),
            '808232536': ('4036956000000076297', 'SAP AppStore', True, ''),
            '822741658': ('4373186000000078309', 'SAP AppStore', True, ''),
        },
    ),
    'E600010-05-40': (
        ('Marketing & Selling Expenses', 'Advertising and Promotion'),
        {
            '697686691': ('2031056000005127041', 'Ariba and other SMS', True, ''),
            '808232536': ('4036956000000076299', 'Ariba and other SMS', True, ''),
            '822741658': ('4373186000000078311', 'Ariba and other SMS', True, ''),
        },
    ),
    'E600010-05-50': (
        (),
        {
            '808232536': ('4036956000000248882', 'Revenue Share Program Partners', False, 'not_expense_relevant'),
        },
    ),
    'E600010-05-90': (
        ('Marketing & Selling Expenses', 'Advertising and Promotion'),
        {
            '808232536': ('4036956000000076331', 'Other Advertising and Promotions Expenses', True, ''),
        },
    ),
    'E600010-10': (
        ('Marketing & Selling Expenses',),
        {
            '697686691': ('2031056000001047150', 'Conferences', True, ''),
            '808232536': ('4036956000000076255', 'Conferences', True, ''),
            '822741658': ('4373186000000078267', 'Conferences', True, ''),
        },
    ),
    'E600010-10-10': (
        ('Marketing & Selling Expenses', 'Conferences'),
        {
            '697686691': ('2031056000001429305', 'Conferences: Registration', True, ''),
            '808232536': ('4036956000000076271', 'Conferences: Registration', True, ''),
            '822741658': ('4373186000000078283', 'Conferences: Registration', True, ''),
        },
    ),
    'E600010-10-20': (
        ('Marketing & Selling Expenses', 'Conferences'),
        {
            '697686691': ('2031056000018043073', 'Conferences: Registration (Consulting)', True, ''),
            '808232536': ('4036956000001157019', 'Conferences: Registration (Consulting)', True, ''),
        },
    ),
    'E600010-10-20-10': (
        ('Marketing & Selling Expenses', 'Business Travel Expenses - CRM'),
        {
            '697686691': ('2031056000017692042', 'Business Travel Expenses - CRM | Transportation', True, ''),
            '808232536': ('4036956000001009068', 'Business Travel Expenses - CRM | Transportation', True, ''),
            '822741658': ('4373186000000228040', 'Business Travel Expenses - CRM | Transportation', True, ''),
        },
    ),
    'E600010-10-20-20': (
        ('Marketing & Selling Expenses', 'Business Travel Expenses - CRM'),
        {
            '697686691': ('2031056000017692049', 'Business Travel Expenses - CRM | Accommodation', True, ''),
            '808232536': ('4036956000001009075', 'Business Travel Expenses - CRM | Accommodation', True, ''),
            '822741658': ('4373186000000228047', 'Business Travel Expenses - CRM | Accommodation', True, ''),
        },
    ),
    'E600010-10-20-30': (
        ('Marketing & Selling Expenses', 'Business Travel Expenses - CRM'),
        {
            '697686691': ('2031056000017692056', 'Business Travel Expenses - CRM | Food', True, ''),
            '808232536': ('4036956000001009082', 'Business Travel Expenses - CRM | Food', True, ''),
            '822741658': ('4373186000000228054', 'Business Travel Expenses - CRM | Food', True, ''),
        },
    ),
    'E600010-10-30': (
        ('Marketing & Selling Expenses', 'Conferences'),
        {
            '697686691': ('2031056000018043080', 'Conferences: Registration (Cloud Services)', True, ''),
            '808232536': ('4036956000001157042', 'Conferences: Registration (Cloud Services)', True, ''),
        },
    ),
    'E600010-10-50': (
        ('Marketing & Selling Expenses', 'Conferences'),
        {
            '697686691': ('2031056000001427037', 'Conferences: Travel Expenses', True, ''),
            '808232536': ('4036956000000076261', 'Conferences: Travel Expenses', True, ''),
            '822741658': ('4373186000000078273', 'Conferences: Travel Expenses', True, ''),
        },
    ),
    'E600010-10-50-10': (
        ('Marketing & Selling Expenses', 'Conferences', 'Conferences: Travel Expenses'),
        {
            '697686691': ('2031056000010760001', 'Conferences: Travel Expenses | Transportation', True, ''),
            '808232536': ('4036956000000076381', 'Conferences: Travel Expenses | Transportation', True, ''),
            '822741658': ('4373186000000078393', 'Conferences: Travel Expenses | Transportation', True, ''),
        },
    ),
    'E600010-10-50-20': (
        ('Marketing & Selling Expenses', 'Conferences', 'Conferences: Travel Expenses'),
        {
            '697686691': ('2031056000010760009', 'Conferences: Travel Expenses | Accommodation', True, ''),
            '808232536': ('4036956000000076383', 'Conferences: Travel Expenses | Accommodation', True, ''),
            '822741658': ('4373186000000078395', 'Conferences: Travel Expenses | Accommodation', True, ''),
        },
    ),
    'E600010-10-50-30': (
        ('Marketing & Selling Expenses', 'Conferences', 'Conferences: Travel Expenses'),
        {
            '697686691': ('2031056000010760015', 'Conferences: Travel Expenses | Food', True, ''),
            '808232536': ('4036956000000076385', 'Conferences: Travel Expenses | Food', True, ''),
            '822741658': ('4373186000000078397', 'Conferences: Travel Expenses | Food', True, ''),
        },
    ),
    'E600010-10-90': (
        ('Marketing & Selling Expenses', 'Conferences'),
        {
            '697686691': ('2031056000001429001', 'Conferences: Other Expenses', True, ''),
            '808232536': ('4036956000000076263', 'Conferences: Other Expenses', True, ''),
            '822741658': ('4373186000000078275', 'Conferences: Other Expenses', True, ''),
        },
    ),
    'E600010-20': (
        ('Marketing & Selling Expenses',),
        {
            '697686691': ('2031056000017692035', 'Business Travel Expenses - CRM', True, ''),
            '808232536': ('4036956000001009061', 'Business Travel Expenses - CRM', True, ''),
            '822741658': ('4373186000000228033', 'Business Travel Expenses - CRM', True, ''),
        },
    ),
    'E600010-30': (
        ('Marketing & Selling Expenses',),
        {
            '697686691': ('2031056000023094013', 'Marketing Expenses', True, ''),
            '808232536': ('4036956000001954001', 'Marketing Expenses', True, ''),
            '822741658': ('4373186000000580031', 'Marketing Expenses', True, ''),
        },
    ),
    'E600010-30-10': (
        ('Marketing & Selling Expenses', 'Marketing Expenses'),
        {
            '697686691': ('2031056000023745007', 'Marketing Expenses - people', True, ''),
            '808232536': ('4036956000002011001', 'Marketing Expenses - people', True, ''),
            '822741658': ('4373186000000606001', 'Marketing Expenses - people', True, ''),
        },
    ),
    'E600010-30-20': (
        ('Marketing & Selling Expenses', 'Marketing Expenses'),
        {
            '697686691': ('2031056000023745016', 'Marketing Expenses - others', True, ''),
            '808232536': ('4036956000002011010', 'Marketing Expenses - others', True, ''),
            '822741658': ('4373186000000606010', 'Marketing Expenses - others', True, ''),
        },
    ),
    'E600060': (
        ('MS | OpeEx',),
        {
            '697686691': ('2031056000000104489', 'Professional Fees', True, ''),
            '808232536': ('4036956000000076191', 'Professional Fees', True, ''),
            '822741658': ('4373186000000078203', 'Professional Fees', True, ''),
        },
    ),
    'E600060-05': (
        ('Professional Fees',),
        {
            '697686691': ('2031056000007499263', 'Management Services', True, ''),
            '808232536': ('4036956000000076345', 'Management Services', True, ''),
            '822741658': ('4373186000000078357', 'Management Services', True, ''),
        },
    ),
    'E600060-05-05': (
        ('Professional Fees', 'Management Services'),
        {
            '697686691': ('2031056000020914057', 'Management Services - others', True, ''),
            '808232536': ('4036956000001818043', 'Management Services - others', True, ''),
        },
    ),
    'E600060-05-10': (
        ('Professional Fees', 'Management Services'),
        {
            '697686691': ('2031056000018231001', 'Management Services (DN)', True, ''),
            '808232536': ('4036956000001200109', 'Management Services (DN)', True, ''),
        },
    ),
    'E600060-05-20': (
        ('Professional Fees', 'Management Services'),
        {
            '808232536': ('4036956000002602639', 'Management Services (EK)', True, ''),
        },
    ),
    'E600060-10': (
        ('Professional Fees',),
        {
            '697686691': ('2031056000000104465', 'Accounting', True, ''),
            '808232536': ('4036956000000076185', 'Accounting', True, ''),
            '822741658': ('4373186000000078197', 'Accounting', True, ''),
        },
    ),
    'E600060-20': (
        ('Professional Fees',),
        {
            '697686691': ('2031056000000104473', 'Legal Fees', True, ''),
            '808232536': ('4036956000000076187', 'Legal Fees', True, ''),
            '822741658': ('4373186000000078199', 'Legal Fees', True, ''),
        },
    ),
    'E600060-30': (
        ('Professional Fees',),
        {
            '697686691': ('2031056000000104457', 'Fees & Permits', True, ''),
            '808232536': ('4036956000000076183', 'Fees & Permits', True, ''),
            '822741658': ('4373186000000078195', 'Fees & Permits', True, ''),
        },
    ),
    'E600060-40': (
        ('Professional Fees',),
        {
            '697686691': ('2031056000010447001', 'Recruitment Expenses', True, ''),
            '808232536': ('4036956000000076379', 'Recruitment Expenses', True, ''),
            '822741658': ('4373186000000078391', 'Recruitment Expenses', True, ''),
        },
    ),
    'E600060-70': (
        ('Professional Fees',),
        {
            '697686691': ('2031056000000000460', 'Other Expenses', True, ''),
            '808232536': ('4036956000000000460', 'Other Expenses', True, ''),
            '822741658': ('4373186000000000460', 'Other Expenses', True, ''),
        },
    ),
    'E700030': (
        (),
        {
            '697686691': ('2031056000000034003', 'COGS - RECURRING BUSINESS', False, 'not_expense_relevant'),
            '808232536': ('4036956000000034003', 'COGS - Consulting Services', False, 'not_expense_relevant'),
            '822741658': ('4373186000000034003', 'COGS - CORE BUSINESS', False, 'not_expense_relevant'),
        },
    ),
    'E700030-10': (
        (),
        {
            '697686691': ('2031056000001432009', 'COGS - Support BRISKEN Tech / JB', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076395', 'COGS - CONS - Payroll', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078285', 'COGS - Support BRISKEN Tech / JB', False, 'not_expense_relevant'),
        },
    ),
    'E700030-12': (
        (),
        {
            '822741658': ('4373186000000078407', 'COGS - MANAGEMENT SERVICES (DN)', False, 'not_expense_relevant'),
        },
    ),
    'E700030-13': (
        (),
        {
            '697686691': ('2031056000014820256', 'COGS - Recurring Revenue Related (Payroll)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078415', 'COGS - BRISKEN Contractors / Payroll', False, 'not_expense_relevant'),
        },
    ),
    'E700030-14': (
        (),
        {
            '808232536': ('4036956000000167064', 'COGS - Non Recurring Revenue Related (IC Contractors)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078417', 'COGS - InterCompany Fees (clearing)', False, 'not_expense_relevant'),
        },
    ),
    'E700030-15': (
        (),
        {
            '697686691': ('2031056000007495653', 'COGS - Recurring Revenue Related (IC Contractors)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076333', 'COGS - Recurring Revenue Related (IC Contractors)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078345', 'COGS - Third Party Contractors (DEV)', False, 'not_expense_relevant'),
        },
    ),
    'E700030-16': (
        (),
        {
            '822741658': ('4373186000000078473', 'COGS - Third Party Contractor Expense Reimbursements', False, 'not_expense_relevant'),
        },
    ),
    'E700030-17': (
        (),
        {
            '697686691': ('2031056000010346011', 'COGS - Recurring Revenue Related (3rd Party Contractors)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078389', 'COGS - Third Party Contractors (SUPPORT)', False, 'not_expense_relevant'),
        },
    ),
    'E700030-18': (
        (),
        {
            '822741658': ('4373186000000078387', 'COGS - Third Party Contractors (PROJECTS)', False, 'not_expense_relevant'),
        },
    ),
    'E700030-19': (
        ('COGS - RECURRING BUSINESS',),
        {
            '697686691': ('2031056000014161139', 'COGS - DEV Infrastructure (SAP Apps & others)', True, ''),
            '822741658': ('4373186000000078411', 'COGS - DEV Infrastructure (SAP Apps & S/4HANA)', True, ''),
        },
    ),
    'E700030-20': (
        ('COGS - RECURRING BUSINESS',),
        {
            '697686691': ('2031056000001429211', 'COGS - CLOUD Infrastructure (ePaaS)', True, ''),
            '808232536': ('4036956000000076377', 'COGS - CONS - 3rd Party Contractors', True, ''),
            '822741658': ('4373186000000078279', 'COGS - CLOUD Infrastructure (ePaaS)', True, ''),
        },
    ),
    'E700030-20X': (
        (),
        {
            '808232536': ('4036956000000076267', 'COGS - CLOUD Infrastructure (ePaaS)', False, 'not_expense_relevant'),
        },
    ),
    'E700030-22': (
        ('COGS - Consulting Services',),
        {
            '808232536': ('4036956000000260852', 'COGS - CONS - Travel Expense (Third Party Reimbursement)', True, ''),
        },
    ),
    'E700030-23': (
        ('COGS - Consulting Services',),
        {
            '808232536': ('4036956000000076353', 'COGS - CONS - Travel Expenses (paid by Brisken)', True, ''),
        },
    ),
    'E700030-25': (
        ('COGS - RECURRING BUSINESS',),
        {
            '697686691': ('2031056000006562999', 'COGS - CLOUD Infrastructure (not ePaaS)', True, ''),
            '808232536': ('4036956000000076313', 'COGS - CLOUD Infrastructure (not ePaaS)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078325', 'COGS - CLOUD Infrastructure (not ePaaS)', True, ''),
        },
    ),
    'E700030-30': (
        ('COGS - RECURRING BUSINESS',),
        {
            '697686691': ('2031056000001432081', 'COGS - Other Infra and IT Costs for Cloud Business', True, ''),
            '808232536': ('4036956000000076277', 'COGS - Other Infra and IT Costs for Cloud Business', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078289', 'COGS - Other Infra and IT Costs for Cloud Business', True, ''),
        },
    ),
    'E700030-40': (
        ('COGS - RECURRING BUSINESS',),
        {
            '697686691': ('2031056000003608003', 'COGS - Compliance and Certifications', True, ''),
            '808232536': ('4036956000000076295', 'COGS - Compliance and Certifications', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078307', 'COGS - Compliance and Certifications', True, ''),
        },
    ),
    'E700030-50': (
        ('COGS - RECURRING BUSINESS',),
        {
            '697686691': ('2031056000005695801', 'COGS - Business Insurance Policies', True, ''),
            '808232536': ('4036956000000076309', 'COGS - CONS - Business Insurance Policies', True, ''),
            '822741658': ('4373186000000078321', 'COGS - Business Insurance Policies', True, ''),
        },
    ),
    'E700030-60': (
        ('COGS - CORE BUSINESS',),
        {
            '822741658': ('4373186000000078365', 'COGS - Travel Expenses (paid by Brisken)', True, ''),
        },
    ),
    'E700030-70': (
        (),
        {
            '697686691': ('2031056000011424017', 'COGS - Taxes, Discounts, Other Reductions', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076387', 'COGS - Taxes, Discounts, Other Reductions', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078399', 'COGS - Taxes, Discounts, Other Reductions', False, 'not_expense_relevant'),
        },
    ),
    'E700030-80': (
        (),
        {
            '697686691': ('2031056000015179464', 'COGS - Revenue Share Program Partners', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078435', 'COGS - Revenue Share Program Partners', False, 'not_expense_relevant'),
        },
    ),
    'E700030-90': (
        (),
        {
            '697686691': ('2031056000017717014', 'COGS - Product Related (Staff Domestic)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000237008', 'COGS - Software Domestic R&D', False, 'not_expense_relevant'),
        },
    ),
    'E700030-91': (
        (),
        {
            '808232536': ('4036956000002334015', 'COGS - Software Domestic R&D - IC Contractors', False, 'not_expense_relevant'),
        },
    ),
    'E700030-92': (
        (),
        {
            '808232536': ('4036956000002334024', 'COGS - Software Domestic R&D - 3rd Party Contractors', False, 'not_expense_relevant'),
        },
    ),
    'E700030-95': (
        (),
        {
            '697686691': ('2031056000017717021', 'COGS - Product Related (Staff International)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000237015', 'COGS - Software International R&D', False, 'not_expense_relevant'),
        },
    ),
    'E700030-96': (
        (),
        {
            '808232536': ('4036956000002334033', 'COGS - Software International R&D - IC Contractors', False, 'not_expense_relevant'),
        },
    ),
    'E700030-97': (
        (),
        {
            '808232536': ('4036956000002334042', 'COGS - Software International R&D - 3rd Party Contractors', False, 'not_expense_relevant'),
        },
    ),
    'E700035': (
        (),
        {
            '808232536': ('4036956000002602109', 'COGS - Cloud Services', False, 'not_expense_relevant'),
        },
    ),
    'E700035-10': (
        (),
        {
            '808232536': ('4036956000002602126', 'COGS - CS - RECURRING', False, 'not_expense_relevant'),
        },
    ),
    'E700035-10-10': (
        (),
        {
            '808232536': ('4036956000000167057', 'COGS - CS - RECURRING - Payroll', False, 'not_expense_relevant'),
        },
    ),
    'E700035-10-15': (
        (),
        {
            '808232536': ('4036956000000076273', 'COGS - CS - RECURRING - Support BCS', False, 'not_expense_relevant'),
        },
    ),
    'E700035-10-20': (
        (),
        {
            '808232536': ('4036956000002602533', 'COGS - CS - RECURRING - Third-Party Contractors', False, 'not_expense_relevant'),
        },
    ),
    'E700035-10-30': (
        (),
        {
            '808232536': ('4036956000002602551', 'COGS - CS - RECURRING - Infrastructure', False, 'not_expense_relevant'),
        },
    ),
    'E700035-10-30-10': (
        (),
        {
            '808232536': ('4036956000002602598', 'COGS - CS - RECCURING - INFRA - BCS Fees', False, 'not_expense_relevant'),
        },
    ),
    'E700035-10-30-20': (
        ('COGS - Cloud Services', 'COGS - CS - RECURRING', 'COGS - CS - RECURRING - Infrastructure'),
        {
            '808232536': ('4036956000002602611', 'COGS - CS - RECURRING - INFRA - Other (SAP Apps, AWS, others)', True, ''),
        },
    ),
    'E700035-50': (
        (),
        {
            '808232536': ('4036956000002602139', 'COGS - CS - NON-RECURRING', False, 'not_expense_relevant'),
        },
    ),
    'E700035-50-10': (
        (),
        {
            '808232536': ('4036956000002028001', 'COGS - CS - NON-RECURRING - Payroll', False, 'not_expense_relevant'),
        },
    ),
    'E700035-50-15': (
        (),
        {
            '808232536': ('4036956000002602542', 'COGS - CS - NON-RECURRING - Support BCS', False, 'not_expense_relevant'),
        },
    ),
    'E700035-50-20': (
        (),
        {
            '808232536': ('4036956000000076375', 'COGS - CS - NON-RECURRING - 3rd Party Contractors', False, 'not_expense_relevant'),
        },
    ),
    'E700035-50-40': (
        (),
        {
            '808232536': ('4036956000002028015', 'COGS - CS - NON-RECURRING - Onboarding Activities IC Staff', False, 'not_expense_relevant'),
        },
    ),
    'E700035-70': (
        (),
        {
            '808232536': ('4036956000002602152', 'COGS - CS - PRODUCT DEV', False, 'not_expense_relevant'),
        },
    ),
    'E700035-70-10': (
        (),
        {
            '808232536': ('4036956000001028223', 'COGS - CS - DEV - Payroll', False, 'not_expense_relevant'),
        },
    ),
    'E700035-70-15': (
        (),
        {
            '808232536': ('4036956000002602630', 'COGS - CS - DEV - Support BCS', False, 'not_expense_relevant'),
        },
    ),
    'E700035-70-20': (
        (),
        {
            '808232536': ('4036956000001028230', 'COGS - CS - DEV - Thirdparty Contractors', False, 'not_expense_relevant'),
        },
    ),
    'E700035-70-30': (
        (),
        {
            '808232536': ('4036956000002602568', 'COGS - CS - DEV - Infrastructure', False, 'not_expense_relevant'),
        },
    ),
    'E700035-70-30-10': (
        (),
        {
            '808232536': ('4036956000002602581', 'COGS - CS - DEV - INFRA - BCS Fees', False, 'not_expense_relevant'),
        },
    ),
    'E700035-70-30-20': (
        ('COGS - Cloud Services', 'COGS - CS - PRODUCT DEV', 'COGS - CS - DEV - Infrastructure'),
        {
            '808232536': ('4036956000000076399', 'COGS - CS - DEV - INFRA - Other (SAP Apps, AWS, others)', True, ''),
        },
    ),
    'E700040': (
        (),
        {
            '697686691': ('2031056000003219511', 'COGS - INTER COMPANY', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076293', 'COGS - INTER COMPANY', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078305', 'COGS - INTER COMPANY', False, 'not_expense_relevant'),
        },
    ),
    'E700040-12': (
        (),
        {
            '697686691': ('2031056000013981072', 'COGS - MANAGEMENT SERVICES (DN) (INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076397', 'COGS - MANAGEMENT SERVICES (DN) (INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078409', 'COGS - MANAGEMENT SERVICES (DN) (INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-13': (
        (),
        {
            '697686691': ('2031056000007862461', 'COGS - BRISKEN Contractors / Payroll (INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076351', 'COGS - BRISKEN Contractors / Payroll (INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078363', 'COGS - BRISKEN Contractors / Payroll (INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-14': (
        (),
        {
            '697686691': ('2031056000007490327', 'COGS - Fees InterCompany (INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076323', 'COGS - Fees InterCompany (INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078335', 'COGS - Fees InterCompany (INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-15': (
        (),
        {
            '697686691': ('2031056000005127271', 'COGS - Third Party Contractors (Bodyshopping)(INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076305', 'COGS - Third Party Contractors (Bodyshopping)(INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078317', 'COGS - Third Party Contractors (Bodyshopping)(INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-16': (
        (),
        {
            '697686691': ('2031056000000465029', 'COGS - Third Party Contractor Expense Reimbursements (INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076245', 'COGS - Third Party Contractor Expense Reimbursements (INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078257', 'COGS - Third Party Contractor Expense Reimbursements (INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-18': (
        (),
        {
            '697686691': ('2031056000000104521', 'COGS - Third Party Contractor (PROJECTS)(INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076197', 'COGS - Third Party Contractor (PROJECTS)(INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078209', 'COGS - Third Party Contractor (PROJECTS)(INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-19': (
        (),
        {
            '697686691': ('2031056000001429219', 'COGS - SAP Infrastructure (SAP Apps & S/4HANA)(INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076269', 'COGS - SAP Infrastructure (SAP Apps & S/4HANA)(INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078281', 'COGS - SAP Infrastructure (SAP Apps & S/4HANA)(INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-20': (
        (),
        {
            '697686691': ('2031056000015179471', 'COGS - CLOUD Infrastructure (ePaaS)(INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000248889', 'COGS - CLOUD Infrastructure (ePaaS)(INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078437', 'COGS - CLOUD Infrastructure (ePaaS)(INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-25': (
        (),
        {
            '697686691': ('2031056000015179478', 'COGS - CLOUD Infrastructure (not ePaaS)(INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000248896', 'COGS - CLOUD Infrastructure (not ePaaS)(INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078439', 'COGS - CLOUD Infrastructure (not ePaaS)(INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-30': (
        (),
        {
            '697686691': ('2031056000015179485', 'COGS - Other Infra and IT Costs for Cloud Business(INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000248903', 'COGS - Other Infra and IT Costs for Cloud Business(INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078441', 'COGS - Other Infra and IT Costs for Cloud Business(INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-40': (
        (),
        {
            '697686691': ('2031056000014820270', 'COGS - Compliance and Certifications (INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000167071', 'COGS - Compliance and Certifications (INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078419', 'COGS - Compliance and Certifications (INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-50': (
        (),
        {
            '697686691': ('2031056000014820277', 'COGS - Business Insurance Policies (INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000167078', 'COGS - Business Insurance Policies (INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078421', 'COGS - Business Insurance Policies (INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-60': (
        (),
        {
            '697686691': ('2031056000001489040', 'COGS - Travel Expenses (paid by Brisken)(INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076283', 'COGS - Travel Expenses (paid by Brisken)(INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078295', 'COGS - Travel Expenses (paid by Brisken)(INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-70': (
        (),
        {
            '697686691': ('2031056000015179492', 'COGS - Taxes, Discounts, Other Reductions(INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000248910', 'COGS - Taxes, Discounts, Other Reductions(INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078443', 'COGS - Taxes, Discounts, Other Reductions(INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700040-80': (
        (),
        {
            '697686691': ('2031056000015179499', 'COGS - Revenue Share Program Partners (INTER COMPANY)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000248917', 'COGS - Revenue Share Program Partners (INTER COMPANY)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078445', 'COGS - Revenue Share Program Partners (INTER COMPANY)', False, 'not_expense_relevant'),
        },
    ),
    'E700050': (
        (),
        {
            '697686691': ('2031056000033061185', 'COGS - NON-RECURRING BUSINESS', False, 'not_expense_relevant'),
        },
    ),
    'E700050-12': (
        (),
        {
            '697686691': ('2031056000013981066', 'COGS - Non Recurring Revenue Related (Payroll)', False, 'not_expense_relevant'),
        },
    ),
    'E700050-14': (
        (),
        {
            '697686691': ('2031056000014820263', 'COGS - Non Recurring Revenue Related (IC Contractors)', False, 'not_expense_relevant'),
        },
    ),
    'E700050-16': (
        (),
        {
            '697686691': ('2031056000010346017', 'COGS - Non Recurring Revenue Related (3rd Party Contractors)', False, 'not_expense_relevant'),
        },
    ),
    'E700050-18': (
        (),
        {
            '697686691': ('2031056000015225928', 'COGS - Third Party Contractor Expense Reimbursements', False, 'not_expense_relevant'),
        },
    ),
    'E700050-60': (
        ('COGS - NON-RECURRING BUSINESS',),
        {
            '697686691': ('2031056000007879367', 'COGS - Travel Expenses (paid by Brisken)', True, ''),
        },
    ),
    'E700050-81': (
        (),
        {
            '697686691': ('2031056000023948003', 'COGS - Onboarding Activities Own Staff', False, 'not_expense_relevant'),
        },
    ),
    'E700050-82': (
        (),
        {
            '697686691': ('2031056000023948012', 'COGS - Onboarding Activities IC Staff', False, 'not_expense_relevant'),
        },
    ),
    'E800010': (
        (),
        {
            '697686691': ('2031056000000104497', 'Amortization Expense', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076193', 'Amortization Expense', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078205', 'Amortization Expense', False, 'not_expense_relevant'),
        },
    ),
    'E800040': (
        (),
        {
            '697686691': ('2031056000000000415', 'Exchange Gain or Loss', False, 'not_expense_relevant'),
            '808232536': ('4036956000000000415', 'Exchange Gain or Loss', False, 'not_expense_relevant'),
            '822741658': ('4373186000000000415', 'CorpServ | Exchange Gain or Loss', False, 'not_expense_relevant'),
        },
    ),
    'E800050': (
        (),
        {
            '697686691': ('2031056000000104375', 'Interest Expense', True, ''),
            '808232536': ('4036956000000076169', 'Interest Expense', True, ''),
            '822741658': ('4373186000000078181', 'Interest Expense', True, ''),
        },
    ),
    'E800100': (
        (),
        {
            '697686691': ('2031056000000181981', 'Taxes Paid', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076233', 'Taxes Paid', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078245', 'Taxes Paid', False, 'not_expense_relevant'),
        },
    ),
    'E900010': (
        (),
        {
            '697686691': ('2031056000001437001', 'Tax Paid', True, ''),
            '808232536': ('4036956000000076279', 'Tax Paid', True, ''),
            '822741658': ('4373186000000078291', 'CorpServ | Tax Paid', True, ''),
        },
    ),
    'E900020': (
        (),
        {
            '697686691': ('2031056000018043283', 'Tax Management Services - Holding', True, ''),
            '808232536': ('4036956000001157094', 'Tax Management Services - Holding', True, ''),
        },
    ),
    'I600000': (
        (),
        {
            '697686691': ('2031056000000439041', 'Income Consulting', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076243', 'Income Consulting', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078255', 'Income Consulting', False, 'not_expense_relevant'),
        },
    ),
    'I600000-05': (
        (),
        {
            '697686691': ('2031056000017000531', 'Income Consulting RAPSODY', False, 'not_expense_relevant'),
            '808232536': ('4036956000000803505', 'Income - CONS - RAPSODY', False, 'not_expense_relevant'),
            '822741658': ('4373186000000159326', 'Income Consulting RAPSODY', False, 'not_expense_relevant'),
        },
    ),
    'I600000-10': (
        (),
        {
            '697686691': ('2031056000000104529', 'Income Consulting SAP (projects)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076199', 'Income - CONS - SAP Projects', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078211', 'Income Consulting SAP (projects)', False, 'not_expense_relevant'),
        },
    ),
    'I600000-20': (
        (),
        {
            '697686691': ('2031056000000663133', 'Income Consulting (support desk services)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076253', 'Income - CONS - Support Desk Services', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078265', 'Income Consulting (support desk services)', False, 'not_expense_relevant'),
        },
    ),
    'I600000-30': (
        (),
        {
            '697686691': ('2031056000014861875', 'Income Consulting (bodyshopping)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000180794', 'Income - CONS - Body Shopping (SAP, etc.)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078423', 'Income Consulting (bodyshopping)', False, 'not_expense_relevant'),
        },
    ),
    'I600000-40': (
        (),
        {
            '697686691': ('2031056000014861880', 'Income Consulting Non Recurring Cloud Related Services', False, 'not_expense_relevant'),
            '808232536': ('4036956000000180799', 'Income Consulting Non Recurring Cloud Related Services', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078425', 'Income Consulting Non Recurring Cloud Related Services', False, 'not_expense_relevant'),
        },
    ),
    'I600000-40-20': (
        (),
        {
            '697686691': ('2031056000014861890', 'Income Consulting Cloud Onboarding (non-recurring)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000180809', 'Income Consulting Cloud Onboarding (non-recurring)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078429', 'Income Consulting Cloud Onboarding (non-recurring)', False, 'not_expense_relevant'),
        },
    ),
    'I600000-40-30': (
        (),
        {
            '697686691': ('2031056000014861895', 'Income Consulting Cloud Maintenance and Support (non-recurring)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000180814', 'Income Consulting Cloud Maintenance and Support (non-recurring)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078431', 'Income Consulting Cloud Maintenance and Support (non-recurring)', False, 'not_expense_relevant'),
        },
    ),
    'I600000-40-40': (
        (),
        {
            '697686691': ('2031056000015179506', 'Income Consulting Cloud Development (non-recurring)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000250899', 'Income Consulting Cloud Development (non-recurring)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078447', 'Income Consulting Cloud Development (non-recurring)', False, 'not_expense_relevant'),
        },
    ),
    'I600000-50': (
        (),
        {
            '697686691': ('2031056000001475002', 'Income Consulting Comission on 3rd Party Apps', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076281', 'Income Consulting Comission on 3rd Party Apps', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078293', 'Income Consulting Comission on 3rd Party Apps', False, 'not_expense_relevant'),
        },
    ),
    'I600000-90': (
        (),
        {
            '697686691': ('2031056000000373001', 'Income Expense Reimbursement - CONSULTING', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076235', 'Income - CONS - Expense Reimbursement', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078247', 'Income Expense Reimbursement - CONSULTING', False, 'not_expense_relevant'),
        },
    ),
    'I600500': (
        (),
        {
            '697686691': ('2031056000003215504', 'Income Cloud Business', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076289', 'Income Cloud Services', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078301', 'Income Cloud Business', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10': (
        (),
        {
            '697686691': ('2031056000007862143', 'RECURRING REVENUE', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076347', 'Income - CS - RECURRING', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078359', 'Income Cloud - RECURRING', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-10': (
        (),
        {
            '697686691': ('2031056000000104541', 'Income Cloud Subscriptions (recurring)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076203', 'Income - CS - RECURRING - Subscriptions', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078215', 'Income Cloud Subscriptions (recurring)', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-10-10': (
        (),
        {
            '697686691': ('2031056000007490279', 'Income Cloud - OnePilot-MDH Subscription', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076315', 'Income - CS - RECURRING - MDH', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078327', 'Income Cloud - OnePilot-MDH Subscription', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-10-20': (
        (),
        {
            '697686691': ('2031056000007490283', 'Income Cloud - OnePilot-Trade Automation Subscription', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076317', 'Income - CS - RECURRING - Smart Trading', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078329', 'Income Cloud - OnePilot-Trade Automation Subscription', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-10-30': (
        (),
        {
            '697686691': ('2031056000007490287', 'Income Cloud - OnePilot / T+ Subscription Platform', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076319', 'Income - CS - RECURRING - OnePilot (Platform)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078331', 'Income Cloud - OnePilot / T+ Subscription Platform', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-10-41': (
        (),
        {
            '697686691': ('2031056000017000536', 'Income Cloud - OnePilot - Cash Flow & Exposure Hub', False, 'not_expense_relevant'),
            '808232536': ('4036956000000803510', 'Income Cloud - OnePilot - Cash Flow & Exposure Hub', False, 'not_expense_relevant'),
            '822741658': ('4373186000000159331', 'Income Cloud - OnePilot - Cash Flow & Exposure Hub', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-10-42': (
        (),
        {
            '697686691': ('2031056000017000541', 'Income Cloud - OnePilot - Credit Data', False, 'not_expense_relevant'),
            '808232536': ('4036956000000803515', 'Income Cloud - OnePilot - Credit Data', False, 'not_expense_relevant'),
            '822741658': ('4373186000000159336', 'Income Cloud - OnePilot - Credit Data', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-10-43': (
        (),
        {
            '697686691': ('2031056000017000546', 'Income Cloud - OnePilot - Bank Statement Generator', False, 'not_expense_relevant'),
            '808232536': ('4036956000000803520', 'Income Cloud - OnePilot - Bank Statement Generator', False, 'not_expense_relevant'),
            '822741658': ('4373186000000159341', 'Income Cloud - OnePilot - Bank Statement Generator', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-10-44': (
        (),
        {
            '697686691': ('2031056000017000551', 'Income Cloud - OnePilot - MDH for Financial Services', False, 'not_expense_relevant'),
            '808232536': ('4036956000000803525', 'Income Cloud - OnePilot - MDH for Financial Services', False, 'not_expense_relevant'),
            '822741658': ('4373186000000159346', 'Income Cloud - OnePilot - MDH for Financial Services', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-10-45': (
        (),
        {
            '697686691': ('2031056000017000556', 'Income Cloud - OnePilot - MDH for Commodities', False, 'not_expense_relevant'),
            '808232536': ('4036956000000803530', 'Income - CS - RECURRING - MDH for Commodities', False, 'not_expense_relevant'),
            '822741658': ('4373186000000159351', 'Income Cloud - OnePilot - MDH for Commodities', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-10-46': (
        (),
        {
            '697686691': ('2031056000017000561', 'Income Cloud - OnePilot - ESH Data Hub', False, 'not_expense_relevant'),
            '808232536': ('4036956000000803535', 'Income Cloud - OnePilot - ESH Data Hub', False, 'not_expense_relevant'),
            '822741658': ('4373186000000159356', 'Income Cloud - OnePilot - ESH Data Hub', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-10-47': (
        (),
        {
            '697686691': ('2031056000017000566', 'Income Cloud - OnePilot - Remittance Advice Gate', False, 'not_expense_relevant'),
            '808232536': ('4036956000000803540', 'Income - CS - RECURRING - Remittance Advice Gate', False, 'not_expense_relevant'),
            '822741658': ('4373186000000159361', 'Income Cloud - OnePilot - Remittance Advice Gate', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-10-48': (
        (),
        {
            '697686691': ('2031056000017000571', 'Income Cloud - OnePilot - Digital Workforce', False, 'not_expense_relevant'),
            '808232536': ('4036956000000803545', 'Income - CS - RECURRING - Digital Workforce', False, 'not_expense_relevant'),
            '822741658': ('4373186000000159366', 'Income Cloud - OnePilot - Digital Workforce', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-10-49': (
        (),
        {
            '697686691': ('2031056000017000576', 'Income Cloud - OnePilot - Bank Fee Portal', False, 'not_expense_relevant'),
            '808232536': ('4036956000000803550', 'Income Cloud - OnePilot - Bank Fee Portal', False, 'not_expense_relevant'),
            '822741658': ('4373186000000159371', 'Income Cloud - OnePilot - Bank Fee Portal', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-20': (
        (),
        {
            '697686691': ('2031056000005127067', 'Income Cloud Premium Service & MDHaaS (recurring)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076301', 'Income - CS - RECURRING - Managed Services', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078313', 'Income Cloud Premium Service & MDHaaS (recurring)', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-20-10': (
        (),
        {
            '697686691': ('2031056000029976007', 'Income Cloud - Premium Support (recurring)', False, 'not_expense_relevant'),
            '808232536': ('4036956000002539001', 'Income Cloud - Premium Support (recurring)', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-20-20': (
        (),
        {
            '697686691': ('2031056000029976014', 'Income Cloud - Managed Services (recurring)', False, 'not_expense_relevant'),
            '808232536': ('4036956000002539008', 'Income - CS - RECURRING - Managed Services for OnePilot (recurring)', False, 'not_expense_relevant'),
        },
    ),
    'I600500-10-20-30': (
        (),
        {
            '697686691': ('2031056000029976025', 'Income Cloud - Market-Data-as-a-Service (recurring)', False, 'not_expense_relevant'),
            '808232536': ('4036956000002539015', 'Income - CS - RECURRING - Market-Data-as-a-Service (recurring)', False, 'not_expense_relevant'),
        },
    ),
    'I600500-40': (
        (),
        {
            '697686691': ('2031056000007862163', 'NON-RECURRING REVENUE', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076349', 'Income - CS - NON-RECURRING', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078361', 'Income Cloud - NON-RECURRING', False, 'not_expense_relevant'),
        },
    ),
    'I600500-40-20': (
        (),
        {
            '697686691': ('2031056000000104547', 'Income Cloud Onboarding (non-recurring)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076205', 'Income - CS - NON-RECURRING - Onboarding (non-recurring)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078217', 'Income Cloud Onboarding (non-recurring)', False, 'not_expense_relevant'),
        },
    ),
    'I600500-40-20-10': (
        (),
        {
            '697686691': ('2031056000017899001', 'Income Cloud Onboarding (non-recurring) Revenue Reallocation to Consulting', False, 'not_expense_relevant'),
            '808232536': ('4036956000001323001', 'Income Cloud Onboarding (non-recurring) Revenue Reallocation to Consulting', False, 'not_expense_relevant'),
        },
    ),
    'I600500-40-30': (
        (),
        {
            '697686691': ('2031056000000104553', 'Income Cloud Maintenance and Support (non-recurring)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076207', 'Income - CS - NON-RECURRING - Maintenance and Support', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078219', 'Income Cloud Maintenance and Support (non-recurring)', False, 'not_expense_relevant'),
        },
    ),
    'I600500-40-30-10': (
        (),
        {
            '697686691': ('2031056000017899006', 'Income Cloud Maintenance and Support (non-recurring) Revenue Reallocation to Consulting', False, 'not_expense_relevant'),
            '808232536': ('4036956000001323006', 'Income Cloud Maintenance and Support (non-recurring) Revenue Reallocation to Consulting', False, 'not_expense_relevant'),
        },
    ),
    'I600500-40-40': (
        (),
        {
            '697686691': ('2031056000014177097', 'Income Cloud Development (non-recurring)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076401', 'Income Cloud Development (non-recurring)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078413', 'Income Cloud Development (non-recurring)', False, 'not_expense_relevant'),
        },
    ),
    'I600500-50': (
        (),
        {
            '697686691': ('2031056000014861900', 'Income Cloud Comission on 3rd Party Apps', False, 'not_expense_relevant'),
            '808232536': ('4036956000000180819', 'Income - CS - NON-RECURRING - Commission on 3rd Party Apps', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078433', 'Income Cloud Comission on 3rd Party Apps', False, 'not_expense_relevant'),
        },
    ),
    'I600500-90': (
        (),
        {
            '697686691': ('2031056000003215837', 'Income Expense Reimbursement - CLOUD', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076291', 'Income - CS - NON-RECURRING - Expense Reimbursement - CLOUD', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078303', 'Income Expense Reimbursement - CLOUD', False, 'not_expense_relevant'),
        },
    ),
    'I600600': (
        (),
        {
            '697686691': ('2031056000005127173', 'Other Income', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076303', 'Other Income', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078315', 'Other Income', False, 'not_expense_relevant'),
        },
    ),
    'I600600-10': (
        (),
        {
            '697686691': ('2031056000000000394', 'Interest Income', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076117', 'Interest Income', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078127', 'CorpServ | Interest Income | Banks', False, 'not_expense_relevant'),
        },
    ),
    'I600600-15': (
        (),
        {
            '822741658': ('4373186000000914153', 'CorpServ | Interest Income | Promissory Notes P/N', False, 'not_expense_relevant'),
        },
    ),
    'I600600-20': (
        (),
        {
            '697686691': ('2031056000000104535', 'Income Corporate Services', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076201', 'Income Corporate Services', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078213', 'CorpServ | Income Corporate Services', False, 'not_expense_relevant'),
        },
    ),
    'I600600-20-10': (
        (),
        {
            '697686691': ('2031056000017722003', 'Management Income - DN', False, 'not_expense_relevant'),
            '808232536': ('4036956000001028090', 'Management Income - DN', False, 'not_expense_relevant'),
            '822741658': ('4373186000000231181', 'CorpServ | Management Income - DN', False, 'not_expense_relevant'),
        },
    ),
    'I600600-20-10-05': (
        (),
        {
            '822741658': ('4373186000000299113', 'CorpServ | Management Services - DN (Consulting)', False, 'not_expense_relevant'),
        },
    ),
    'I600600-20-10-10': (
        (),
        {
            '822741658': ('4373186000000299118', 'CorpServ | Management Services - DN (Cloud)', False, 'not_expense_relevant'),
        },
    ),
    'I600600-20-20': (
        (),
        {
            '697686691': ('2031056000017722008', 'Management Income - CC', False, 'not_expense_relevant'),
            '808232536': ('4036956000001028095', 'Management Income - CC', False, 'not_expense_relevant'),
            '822741658': ('4373186000000231186', 'CorpServ | Management Income - CC', False, 'not_expense_relevant'),
        },
    ),
    'I600600-20-30': (
        (),
        {
            '697686691': ('2031056000017722015', 'Management Income - Compliance & IT', False, 'not_expense_relevant'),
            '808232536': ('4036956000001028100', 'Management Income - Compliance & IT', False, 'not_expense_relevant'),
            '822741658': ('4373186000000231193', 'Management Income - Compliance & IT (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'I600600-20-40': (
        (),
        {
            '697686691': ('2031056000017722020', 'Management Income - Finance & General Mngt', False, 'not_expense_relevant'),
            '808232536': ('4036956000001028105', 'Management Income - FInance & General Mngt', False, 'not_expense_relevant'),
            '822741658': ('4373186000000231198', 'CorpServ | Management Income - Finance and General Mngt', False, 'not_expense_relevant'),
        },
    ),
    'I600900': (
        (),
        {
            '697686691': ('2031056000000000391', 'Receivables Collection', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076115', 'Receivables Collection', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078125', 'Receivables Collection', False, 'not_expense_relevant'),
        },
    ),
    'I600902': (
        (),
        {
            '697686691': ('2031056000000000406', 'Discount', False, 'not_expense_relevant'),
            '808232536': ('4036956000000000406', 'Discount', False, 'not_expense_relevant'),
            '822741658': ('4373186000000000406', 'Discount (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'L100-20-1000-0000': (
        (),
        {
            '697686691': ('2031056000008476063', 'Bank Liabilites', False, 'not_expense_relevant'),
        },
    ),
    'L100-20-1000-0001': (
        (),
        {
            '697686691': ('2031056000000104581', 'Direct Deposit Liabilities', False, 'not_expense_relevant'),
        },
    ),
    'L100-20-1100-6013': (
        (),
        {
            '697686691': ('2031056000015681999', 'VISA 6013 TRAVEL EXPENSE active since 230601', False, 'not_expense_relevant'),
        },
    ),
    'L100-20-1100-8311': (
        (),
        {
            '697686691': ('2031056000002313057', 'Chase United Visa 8311 | business expenses | Dirk Neumann', False, 'not_expense_relevant'),
        },
    ),
    'L100-20-1100-8311Z': (
        (),
        {
            '697686691': ('2031056000000089038', 'Chase United Visa 8311 | business expenses (inactive)', False, 'not_expense_relevant'),
        },
    ),
    'L100-20-1200-2448': (
        (),
        {
            '697686691': ('2031056000016084005', 'Wise Visa 2448 | business expenses | Dirk Neumann', False, 'not_expense_relevant'),
        },
    ),
    'L100-30-1000-0000': (
        (),
        {
            '808232536': ('4036956000000076365', 'Bank Liabilites', False, 'not_expense_relevant'),
        },
    ),
    'L100-30-1000-0001': (
        (),
        {
            '808232536': ('4036956000000076209', 'Direct Deposit Liabilities', False, 'not_expense_relevant'),
        },
    ),
    'L100-30-1100-1176': (
        (),
        {
            '808232536': ('4036956000000803560', 'Chase Visa 1176 | travel expenses | Dirk Neumann', False, 'not_expense_relevant'),
        },
    ),
    'L100-30-1200-1160': (
        (),
        {
            '808232536': ('4036956000000803555', 'Wise Visa 1160 | business expenses | Dirk Neumann', False, 'not_expense_relevant'),
        },
    ),
    'L100-50-1000-0000': (
        (),
        {
            '822741658': ('4373186000000078377', 'Bank Liabilites', False, 'not_expense_relevant'),
        },
    ),
    'L100-50-1000-0001': (
        (),
        {
            '822741658': ('4373186000000078221', 'Direct Deposit Liabilities', False, 'not_expense_relevant'),
        },
    ),
    'L100-50-1100-0000': (
        (),
        {
            '822741658': ('4373186000000154009', 'CHASE VISA - 2838 - TRAVEL', False, 'not_expense_relevant'),
        },
    ),
    'L100-50-1200-3344': (
        (),
        {
            '822741658': ('4373186000000079911', 'Wise Visa 3344 | business expenses | Dirk Neumann', False, 'not_expense_relevant'),
        },
    ),
    'L100-50-1500-0113': (
        (),
        {
            '822741658': ('4373186000000079916', 'GSBANK Apple Master Card 0113 | Dirk Neumann', False, 'not_expense_relevant'),
        },
    ),
    'L180-20-6000-0000': (
        (),
        {
            '697686691': ('2031056000002747013', 'N/P to Shareholders', False, 'not_expense_relevant'),
        },
    ),
    'L180-20-8000-0000': (
        (),
        {
            '697686691': ('2031056000015215155', 'N/P - Related Companies', False, 'not_expense_relevant'),
        },
    ),
    'L180-20-8100-HOLD': (
        (),
        {
            '697686691': ('2031056000015215162', 'N/P - BRISKEN HOLDING', False, 'not_expense_relevant'),
        },
    ),
    'L180-20-8200-CSER': (
        (),
        {
            '697686691': ('2031056000015215169', 'N/P - BRISKEN CLOUD SERVICES', False, 'not_expense_relevant'),
        },
    ),
    'L180-20-8300-CONS': (
        (),
        {
            '697686691': ('2031056000015215176', 'N/P - BRISKEN CONSULTING', False, 'not_expense_relevant'),
        },
    ),
    'L180-20-8400-CSOL': (
        (),
        {
            '697686691': ('2031056000015215183', 'N/P - BRISKEN CLOUD SOLUTIONS', False, 'not_expense_relevant'),
        },
    ),
    'L180-20-8500-CORP': (
        (),
        {
            '697686691': ('2031056000015319708', 'N/P - BRISKEN CORP SERVICES', False, 'not_expense_relevant'),
        },
    ),
    'L180-20-8600-GMBH': (
        (),
        {
            '697686691': ('2031056000015215190', 'N/P - BRISKEN GMBH', False, 'not_expense_relevant'),
        },
    ),
    'L180-30-6000-0000': (
        (),
        {
            '808232536': ('4036956000000076287', 'N/P to Shareholders', False, 'not_expense_relevant'),
        },
    ),
    'L180-30-8000-0000': (
        (),
        {
            '808232536': ('4036956000000258129', 'N/P - Related Companies', False, 'not_expense_relevant'),
        },
    ),
    'L180-30-8100-HOLD': (
        (),
        {
            '808232536': ('4036956000000258136', 'N/P - BRISKEN HOLDING', False, 'not_expense_relevant'),
        },
    ),
    'L180-30-8200-CSER': (
        (),
        {
            '808232536': ('4036956000000258143', 'N/P - BRISKEN CLOUD SERVICES', False, 'not_expense_relevant'),
        },
    ),
    'L180-30-8300-CONS': (
        (),
        {
            '808232536': ('4036956000000258150', 'N/P - BRISKEN CONSULTING', False, 'not_expense_relevant'),
        },
    ),
    'L180-30-8400-CSOL': (
        (),
        {
            '808232536': ('4036956000000258157', 'N/P - BRISKEN CLOUD SOLUTIONS', False, 'not_expense_relevant'),
        },
    ),
    'L180-30-8500-CORP': (
        (),
        {
            '808232536': ('4036956000000286644', 'N/P - BRISKEN CORP SERVICES', False, 'not_expense_relevant'),
        },
    ),
    'L180-30-8600-GMBH': (
        (),
        {
            '808232536': ('4036956000000258164', 'N/P - BRISKEN GMBH', False, 'not_expense_relevant'),
        },
    ),
    'L180-50-6000-0000': (
        (),
        {
            '822741658': ('4373186000000078299', 'N/P to Shareholders', False, 'not_expense_relevant'),
        },
    ),
    'L180-50-8000-0000': (
        (),
        {
            '822741658': ('4373186000000078461', 'N/P - Related Companies', False, 'not_expense_relevant'),
        },
    ),
    'L180-50-8100-HOLD': (
        (),
        {
            '822741658': ('4373186000000078463', 'N/P - BRISKEN HOLDING', False, 'not_expense_relevant'),
        },
    ),
    'L180-50-8200-CSER': (
        (),
        {
            '822741658': ('4373186000000078465', 'N/P - BRISKEN CLOUD SERVICES', False, 'not_expense_relevant'),
        },
    ),
    'L180-50-8300-CONS': (
        (),
        {
            '822741658': ('4373186000000078467', 'N/P - BRISKEN CONSULTING', False, 'not_expense_relevant'),
        },
    ),
    'L180-50-8400-CSOL': (
        (),
        {
            '822741658': ('4373186000000078469', 'N/P - BRISKEN CLOUD SOLUTIONS', False, 'not_expense_relevant'),
        },
    ),
    'L180-50-8500-CORP': (
        (),
        {
            '822741658': ('4373186000000078477', 'N/P - BRISKEN CORP SERVICES', False, 'not_expense_relevant'),
        },
    ),
    'L180-50-8600-GMBH': (
        (),
        {
            '822741658': ('4373186000000078471', 'N/P - BRISKEN GMBH', False, 'not_expense_relevant'),
        },
    ),
    'L200000': (
        (),
        {
            '697686691': ('2031056000000000373', 'Accounts Payable', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076105', 'Accounts Payable', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078115', 'Accounts Payable', False, 'not_expense_relevant'),
        },
    ),
    'L200005': (
        (),
        {
            '697686691': ('2031056000001298093', 'Subcontractor Payables', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076257', 'Subcontractor Payables', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078269', 'Subcontractor Payables', False, 'not_expense_relevant'),
        },
    ),
    'L200010': (
        (),
        {
            '697686691': ('2031056000000000376', 'Tax Payable', False, 'not_expense_relevant'),
            '808232536': ('4036956000000000376', 'Tax Payable', False, 'not_expense_relevant'),
            '822741658': ('4373186000000000376', 'Tax Payable', False, 'not_expense_relevant'),
        },
    ),
    'L200020': (
        (),
        {
            '697686691': ('2031056000000035003', 'Employee Reimbursements', False, 'not_expense_relevant'),
            '808232536': ('4036956000000035003', 'Employee Reimbursements', False, 'not_expense_relevant'),
            '822741658': ('4373186000000035003', 'Employee Reimbursements', False, 'not_expense_relevant'),
        },
    ),
    'L200030': (
        (),
        {
            '697686691': ('2031056000000104617', 'Payroll Liabilities', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076215', 'Payroll Liabilities', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078227', 'Payroll Liabilities', False, 'not_expense_relevant'),
        },
    ),
    'L200030-010': (
        (),
        {
            '697686691': ('2031056000007945039', 'Payroll Liabilities-Salaries And Wages', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076361', 'Payroll Liabilities-Salaries And Wages', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078373', 'Payroll Liabilities-Salaries And Wages', False, 'not_expense_relevant'),
        },
    ),
    'L200030-020': (
        (),
        {
            '697686691': ('2031056000007945033', 'Payroll Liabilities-Payroll Tax Payable', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076355', 'Payroll Liabilities-Payroll Tax Payable', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078367', 'Payroll Liabilities-Payroll Tax Payable', False, 'not_expense_relevant'),
        },
    ),
    'L200030-030': (
        (),
        {
            '697686691': ('2031056000000104607', 'Payroll Liabilities-SEP PAYABLE', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076213', 'Payroll Liabilities-SEP PAYABLE', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078225', 'Payroll Liabilities-SEP PAYABLE', False, 'not_expense_relevant'),
        },
    ),
    'L200030-040': (
        (),
        {
            '697686691': ('2031056000007945035', 'Payroll Liabilities-Benefits Payable', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076357', 'Payroll Liabilities-Benefits Payable', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078369', 'Payroll Liabilities-Benefits Payable', False, 'not_expense_relevant'),
        },
    ),
    'L200030-050': (
        (),
        {
            '697686691': ('2031056000007945037', 'Payroll Liabilities-Deductions Payable', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076359', 'Payroll Liabilities-Deductions Payable', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078371', 'Payroll Liabilities-Deductions Payable', False, 'not_expense_relevant'),
        },
    ),
    'L200040': (
        (),
        {
            '697686691': ('2031056000000005001', 'Unearned Revenue', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076123', 'Unearned Revenue', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078133', 'Unearned Revenue', False, 'not_expense_relevant'),
        },
    ),
    'Q100010': (
        (),
        {
            '697686691': ('2031056000000104631', 'Capital Stock', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076217', 'Capital Stock', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078229', 'Capital Stock', False, 'not_expense_relevant'),
        },
    ),
    'Q100020': (
        (),
        {
            '697686691': ('2031056000000104637', 'Opening Balance Equity', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076219', 'Opening Balance Equity', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078231', 'Opening Balance Equity', False, 'not_expense_relevant'),
        },
    ),
    'Q100025': (
        (),
        {
            '697686691': ('2031056000000000385', 'Opening Balance Offset', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076111', 'Opening Balance Offset', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078121', 'Opening Balance Offset', False, 'not_expense_relevant'),
        },
    ),
    'Q100030': (
        (),
        {
            '697686691': ('2031056000000000379', 'Retained Earnings', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076107', 'Retained Earnings', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078117', 'Retained Earnings', False, 'not_expense_relevant'),
        },
    ),
    'Q100040': (
        (),
        {
            '697686691': ('2031056000000104645', 'Shareholder Distributions (all)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076221', 'Shareholder Distributions (all)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078233', 'Shareholder Distributions (all)', False, 'not_expense_relevant'),
        },
    ),
    'Q100040-05': (
        (),
        {
            '697686691': ('2031056000007495829', 'Distribution to Dirk Neumann - Account Close 12/31/2019 balance', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076341', 'Distribution to Dirk Neumann - Account Close 12/31/2019 balance', False, 'not_expense_relevant'),
        },
    ),
    'Q100040-10': (
        (),
        {
            '697686691': ('2031056000007495825', 'Distribution - Receivables prior to 01/01/2020', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076339', 'Distribution - Receivables prior to 01/01/2020', False, 'not_expense_relevant'),
        },
    ),
    'Q100040-20': (
        (),
        {
            '697686691': ('2031056000007495821', 'Shareholder Distribution - Dirk Neumann - 2021', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076337', 'Shareholder Distribution - Dirk Neumann - 2021', False, 'not_expense_relevant'),
        },
    ),
    'Q100040-2023': (
        (),
        {
            '822741658': ('4373186000000078353', 'Distribution to DN 2023', False, 'not_expense_relevant'),
        },
    ),
    'Q100040-2024': (
        (),
        {
            '822741658': ('4373186000000078351', 'Distribution to DN 2024', False, 'not_expense_relevant'),
        },
    ),
    'Q100040-2025': (
        (),
        {
            '822741658': ('4373186000000078349', 'Distribution to DN 2025', False, 'not_expense_relevant'),
        },
    ),
    'Q100040-2026': (
        (),
        {
            '822741658': ('4373186000000078375', 'Distribution to DN 2026', False, 'not_expense_relevant'),
        },
    ),
    'Q100040-2027': (
        (),
        {
            '822741658': ('4373186000000078401', 'Distribution to DN 2027', False, 'not_expense_relevant'),
        },
    ),
    'Q100040-30': (
        (),
        {
            '697686691': ('2031056000008476009', 'Shareholder Distribution - Dirk Neumann - 2022', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076363', 'Shareholder Distribution - Dirk Neumann - 2022', False, 'not_expense_relevant'),
        },
    ),
    'Q100040-40': (
        (),
        {
            '697686691': ('2031056000013905081', 'Shareholder Distribution - BRISKEN HOLDING LLC', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076389', 'Shareholder Distribution - BRISKEN HOLDING LLC', False, 'not_expense_relevant'),
        },
    ),
    'Q100050': (
        (),
        {
            '697686691': ('2031056000000104651', 'Shareholder Equity', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076223', 'Shareholder Equity', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078235', 'Shareholder Equity', False, 'not_expense_relevant'),
        },
    ),
    'T900900': (
        (),
        {
            '697686691': ('2031056000000045001', 'Tag Adjustments', False, 'not_expense_relevant'),
            '808232536': ('4036956000000045001', 'Tag Adjustments', False, 'not_expense_relevant'),
            '822741658': ('4373186000000045001', 'Tag Adjustments', False, 'not_expense_relevant'),
        },
    ),
    'T900999': (
        (),
        {
            '697686691': ('2031056000000003001', 'Opening Balance Adjustments', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076121', 'Opening Balance Adjustments', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078131', 'Opening Balance Adjustments', False, 'not_expense_relevant'),
        },
    ),
    'Z100000000': (
        (),
        {
            '697686691': ('2031056000005695807', 'Business Insurance (DO NOT USE)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076311', 'Business Insurance (DO NOT USE)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078323', 'Business Insurance (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'Z10000010Z': (
        (),
        {
            '697686691': ('2031056000001382002', 'ZZZ | Cash In Hand | DO NOT USE', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076259', 'Cash In Hand', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078271', 'ZZZ | Cash In Hand | DO NOT USE', False, 'not_expense_relevant'),
        },
    ),
    'Z10000011Z': (
        (),
        {
            '697686691': ('2031056000004947001', 'Purchase Discounts', False, 'not_expense_relevant'),
            '808232536': ('4036956000000072001', 'Purchase Discounts', False, 'not_expense_relevant'),
            '822741658': ('4373186000000072001', 'Purchase Discounts', False, 'not_expense_relevant'),
        },
    ),
    'Z10000012Z': (
        (),
        {
            '697686691': ('2031056000005442008', 'Sales to Customers (Cash)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076307', 'Sales to Customers (Cash)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078319', 'Sales to Customers (Cash)', False, 'not_expense_relevant'),
        },
    ),
    'ZA095-10-1000-0000Z': (
        (),
        {
            '822741658': ('4373186000000078113', 'ZZZ | Cash In Hand | DO NOT USE 2', False, 'not_expense_relevant'),
        },
    ),
    'ZA095-30-1000-0000Z': (
        (),
        {
            '808232536': ('4036956000000076103', 'ZZZ | Cash In Hand | DO NOT USE', False, 'not_expense_relevant'),
        },
    ),
    'ZA180-30-6010-DN01Z': (
        (),
        {
            '808232536': ('4036956000000076211', 'N/P - Dirk Neumann OBSOLETE', False, 'not_expense_relevant'),
        },
    ),
    'ZA500100Z': (
        (),
        {
            '697686691': ('2031056000000000370', 'Advance Tax', False, 'not_expense_relevant'),
            '822741658': ('4373186000000000370', 'Advance Tax', False, 'not_expense_relevant'),
        },
    ),
    'ZA500200Z': (
        (),
        {
            '697686691': ('2031056000000035001', 'Employee Advance', False, 'not_expense_relevant'),
            '822741658': ('4373186000000035001', 'Employee Advance', False, 'not_expense_relevant'),
        },
    ),
    'ZA500400Z': (
        (),
        {
            '697686691': ('2031056000000034001', 'Inventory Asset (DO NOT USE)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078139', 'Inventory Asset (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'ZE100035Z': (
        (),
        {
            '697686691': ('2031056000000032023', 'Lodging (DO NOT USE)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000032023', 'Lodging (DO NOT USE)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000032023', 'Lodging (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'ZE100035Z2': (
        (),
        {
            '822741658': ('4373186000000078109', 'Lodging 2 (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'ZE100035Z3': (
        (),
        {
            '822741658': ('4373186000000078137', 'Lodging 3 (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'ZE100080Z': (
        (),
        {
            '697686691': ('2031056000000104295', 'Misc Expense (NO LONGER USED)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076153', 'Misc Expense (NO LONGER USED)', False, 'not_expense_relevant'),
        },
    ),
    'ZE300040Z1': (
        (),
        {
            '822741658': ('4373186000000078479', 'Salaries and Employee Wages (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'ZE400030Z': (
        (),
        {
            '697686691': ('2031056000000104359', 'Insurance Expense (DO NOT USE)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076165', 'Insurance Expense (DO NOT USE)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078177', 'Insurance Expense (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'ZE400040Z': (
        (),
        {
            '697686691': ('2031056000000104367', 'Insurance Expense:General Lia…(NO LONGER USED)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076167', 'Insurance Expense:General Lia…(NO LONGER USED)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078179', 'Insurance Expense:General Lia…(NO LONGER USED)', False, 'not_expense_relevant'),
        },
    ),
    'ZE500010-50Z': (
        (),
        {
            '697686691': ('2031056000000110961', 'IT: Other IT expenses, fees, etc. (DO NOT USE)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076231', 'IT: Other IT expenses, fees, etc. (DO NOT USE)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078243', 'IT: Other IT expenses, fees, etc. (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'ZE500020Z': (
        (),
        {
            '697686691': ('2031056000000104399', 'Dues and Subscriptions (NO LONGER USED)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076175', 'Dues and Subscriptions (NO LONGER USED)', False, 'not_expense_relevant'),
        },
    ),
    'ZE700020Z': (
        (),
        {
            '697686691': ('2031056000000035005', 'Uncategorized (DO NOT USE)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000035005', 'Uncategorized (DO NOT USE)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000035005', 'Uncategorized (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'ZE999999Z': (
        (),
        {
            '697686691': ('2031056000000104507', 'Ask My Accountant', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076195', 'Ask My Accountant (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'ZI600000-40-10Z': (
        (),
        {
            '697686691': ('2031056000014861885', 'Income Consulting Cloud Onboarding (non-recurring)(DO NOT USE)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000180804', 'Income Consulting Cloud Onboarding (non-recurring)(DO NOT USE)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078427', 'Income Consulting Cloud Onboarding (non-recurring)(DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'ZI600500-20-10Z': (
        (),
        {
            '697686691': ('2031056000007490299', 'Income Cloud Non Recurring (DO NOT USE)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076321', 'Income Cloud Non Recurring (DO NOT USE)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078333', 'Income Cloud Non Recurring (DO NOT USE)', False, 'not_expense_relevant'),
        },
    ),
    'ZI600903Z': (
        (),
        {
            '697686691': ('2031056000000000397', 'Late Fee Income (not in use)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000000397', 'Late Fee Income (not in use)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000000397', 'Late Fee Income (not in use)', False, 'not_expense_relevant'),
        },
    ),
    'ZI600904Z': (
        (),
        {
            '697686691': ('2031056000000010001', 'Sale Adjustments (not in use)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000010001', 'Sale Adjustments (not in use)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000010001', 'Sale Adjustments (not in use)', False, 'not_expense_relevant'),
        },
    ),
    'ZI600905Z': (
        (),
        {
            '697686691': ('2031056000000000388', 'Sales (not in use)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076113', 'Sales (not in use)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078123', 'Sales (not in use)', False, 'not_expense_relevant'),
        },
    ),
    'ZI600906Z': (
        (),
        {
            '697686691': ('2031056000000014001', 'Shipping Charge (not in use)', False, 'not_expense_relevant'),
            '808232536': ('4036956000000014001', 'Shipping Charge (not in use)', False, 'not_expense_relevant'),
            '822741658': ('4373186000000014001', 'Shipping Charge (not in use)', False, 'not_expense_relevant'),
        },
    ),
    'ZL100-20-1100-6013Z1': (
        (),
        {
            '697686691': ('2031056000001022006', 'BUSINESS CARD 6013  (20201 - 200612)', False, 'not_expense_relevant'),
        },
    ),
    'ZL100-20-1100-6013Z2': (
        (),
        {
            '697686691': ('2031056000002313053', 'BUSINESS CARD 6013 (200915 - 210829)', False, 'not_expense_relevant'),
        },
    ),
    'ZL100-20-1100-6013Z3': (
        (),
        {
            '697686691': ('2031056000007688006', 'BUSINESS CARD 6013 (211017 - 230602)', False, 'not_expense_relevant'),
        },
    ),
    'ZQ200010Z': (
        (),
        {
            '697686691': ('2031056000000012001', 'Drawings', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076125', 'Drawings', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078135', 'Drawings', False, 'not_expense_relevant'),
        },
    ),
    'ZQ200020Z': (
        (),
        {
            '697686691': ('2031056000000104659', 'Open Balance Offset', False, 'not_expense_relevant'),
            '808232536': ('4036956000000076225', 'Open Balance Offset', False, 'not_expense_relevant'),
            '822741658': ('4373186000000078237', 'Open Balance Offset', False, 'not_expense_relevant'),
        },
    ),
    'ZQ200030Z': (
        (),
        {
            '697686691': ('2031056000000000382', "Owner's Equity", False, 'not_expense_relevant'),
            '808232536': ('4036956000000076109', "Owner's Equity", False, 'not_expense_relevant'),
            '822741658': ('4373186000000078119', "Owner's Equity", False, 'not_expense_relevant'),
        },
    ),
}
