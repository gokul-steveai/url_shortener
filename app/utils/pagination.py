from math import ceil


def build_paginated_response(
    items: list,
    total: int,
    page: int,
    limit: int,
):
    pages = ceil(total / limit) if limit else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }
