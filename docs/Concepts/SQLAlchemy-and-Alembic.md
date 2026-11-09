---
title: "SQLAlchemy (ORM) and Alembic (migrations)"
date: 2026-11-08
tags: [concept, database, python]
---
# SQLAlchemy and Alembic

## SQLAlchemy: an ORM
An **ORM** (object-relational mapper) lets you work with tables as Python classes instead of writing raw SQL everywhere:
```python
class Projection(Base):
    __tablename__ = "projections"
    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    week: Mapped[int]
    points: Mapped[float]

session.scalars(select(Projection).where(Projection.week == 10))
```
SQLAlchemy translates that into SQL. It also prevents **SQL injection** (a classic security bug) by never pasting user input into query text.

## Alembic: migrations
Your tables will change over time ("add an `injury_status` column"). A **migration** is a small numbered script describing one change:
```
alembic/versions/
  0001_create_users_leagues.py
  0002_add_projections.py
  0003_add_injury_status.py
```
Alembic records which migrations a database has already had and applies only the missing ones, **the same way on your laptop, in CI and in production**. In Sunday War Room, CD runs `alembic upgrade head` on deploy, so nobody ever edits the production database by hand.

## Lesson from the old project
The old app had to hand-bump a `SCHEMA_VERSION` and sometimes rebuild the database file, because `create_all()` never adds columns to existing tables. Alembic is the proper fix.

Related: [Databases](Databases.md) · [ADR-015](../Decisions/ADR-015-Database-PostgreSQL.md) · [CI/CD](CI-CD-GitHub-Actions.md)
