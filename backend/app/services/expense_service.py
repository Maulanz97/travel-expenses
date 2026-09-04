from decimal import Decimal, ROUND_DOWN
from app.services.group_service import get_group_membership

def calculate_shares(
    amount: Decimal,
    payer_id: int,
    participants: list[int]
):
    if len(participants) == 0:
        return {
            "message": "At least one participant is required"
        }

    # Convert the total amount to cents
    total_cents = int(
        (amount * 100).quantize(
            Decimal("1"),
            rounding=ROUND_DOWN
        )
    )

    # Base amount that every participant receives
    base_share = total_cents // len(participants)

    # Remaining cents after the equal division
    remainder = total_cents % len(participants)

    shares = {}

    for user_id in participants:
        shares[user_id] = base_share

    # Give the remaining cents to the payer
    if payer_id in shares:
        shares[payer_id] += remainder
    else:
        # If the payer is not a participant,
        # assign the remainder to the first participant.
        shares[participants[0]] += remainder

    return shares


def calculate_equal_split(
    amount: Decimal,
    payer_id: int,
    participants: list[int]
):
    shares = calculate_shares(
        amount=amount,
        payer_id=payer_id,
        participants=participants
    )

    if isinstance(shares, dict) and "message" in shares:
        return shares

    result = []

    for user_id in participants:
        share = Decimal(shares[user_id]) / Decimal("100")

        result.append({
            "user_id": user_id,
            "share": share
        })

    return {
        "amount": amount,
        "participants": len(participants),
        "shares": result
    }


def calculate_balances(
    amount: Decimal,
    payer_id: int,
    participants: list[int]
):
    shares = calculate_shares(
        amount=amount,
        payer_id=payer_id,
        participants=participants
    )

    if isinstance(shares, dict) and "message" in shares:
        return shares

    balances = []

    for user_id in participants:
        share = Decimal(shares[user_id]) / Decimal("100")

        balances.append({
            "user_id": user_id,
            "paid": amount if user_id == payer_id else Decimal("0.00"),
            "share": share,
            "balance": (
                amount - share
                if user_id == payer_id
                else -share
            )
        })

    # If the payer is not a participant,
    # they still receive credit for the full amount paid.
    if payer_id not in participants:
        balances.append({
            "user_id": payer_id,
            "paid": amount,
            "share": Decimal("0.00"),
            "balance": amount
        })

    return balances

def calculate_group_balances(expenses_data):
    balances = {}

    for expense in expenses_data:
        amount = Decimal(expense["amount"])
        payer_id = expense["payer_id"]
        participants = expense["participants"]

        if len(participants) == 0:
            continue

        shares = calculate_shares(
            amount=amount,
            payer_id=payer_id,
            participants=participants
        )

        if isinstance(shares, dict) and "message" in shares:
            continue

        # Every participant owes their calculated share
        for user_id in participants:
            if user_id not in balances:
                balances[user_id] = Decimal("0.00")

            share = Decimal(shares[user_id]) / Decimal("100")
            balances[user_id] -= share

        # The payer receives credit for the full amount paid
        if payer_id not in balances:
            balances[payer_id] = Decimal("0.00")

        balances[payer_id] += amount

    return balances

def calculate_settlements(balances):
    creditors = [
        {
            "user_id": user_id,
            "amount": balance
        }
        for user_id, balance in balances.items()
        if balance > 0
    ]

    debtors = [
        {
            "user_id": user_id,
            "amount": -balance
        }
        for user_id, balance in balances.items()
        if balance < 0
    ]

    settlements = []

    i = 0
    j = 0

    while i < len(debtors) and j < len(creditors):
        debtor = debtors[i]
        creditor = creditors[j]

        amount = min(
            debtor["amount"],
            creditor["amount"]
        )

        settlements.append({
            "from_user": debtor["user_id"],
            "to_user": creditor["user_id"],
            "amount": amount
        })

        debtor["amount"] -= amount
        creditor["amount"] -= amount

        if debtor["amount"] == 0:
            i += 1

        if creditor["amount"] == 0:
            j += 1

    return settlements

def validate_expense_participants(
    db,
    group_id: int,
    payer_id: int,
    participants: list[int]
):
    from app.models.user import User
    from app.models.group import Group

    # Check group
    group = db.query(Group).filter(
        Group.id == group_id
    ).first()

    if group is None:
        return "Group not found"

    # Check payer
    payer = db.query(User).filter(
        User.id == payer_id
    ).first()

    if payer is None:
        return "Payer not found"

    # Check payer membership
    payer_membership = get_group_membership(payer_id, group_id, db)

    if payer_membership is None:
        return "Payer is not a member of this group"

    # Check participants
    if len(participants) == 0:
        return "At least one participant is required"

    # Prevent duplicates
    if len(participants) != len(set(participants)):
        return "Duplicate participants are not allowed"

    # Check every participant
    for user_id in participants:
        user = db.query(User).filter(
            User.id == user_id
        ).first()

        if user is None:
            return f"User {user_id} not found"

        membership = get_group_membership(user_id, group_id, db)

        if membership is None:
            return (
                f"User {user_id} is not a member "
                "of this group"
            )

    return None