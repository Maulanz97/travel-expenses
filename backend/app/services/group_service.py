from app.models.group_member import GroupMember


def get_group_membership(user_id: int, group_id: int, db):
    return db.query(GroupMember).filter(
        GroupMember.user_id == user_id,
        GroupMember.group_id == group_id
    ).first()