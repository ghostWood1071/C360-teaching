from . import customers, accounts, transactions, customer_profiles, loans

GENERATORS = dict(customers=customers.generate, accounts=accounts.generate, transactions=transactions.generate,
                  customer_profiles=customer_profiles.generate, loans=loans.generate)
