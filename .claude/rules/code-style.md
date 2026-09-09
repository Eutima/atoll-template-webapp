# Code style

Detail for the `code-style` reference in `CLAUDE.md`. These rules override defaults; follow them exactly.
Match the surrounding code's idiom, naming, and comment density in any file you touch.

## Keep diffs minimal

- Don't reflow or restyle code you aren't otherwise changing. No style-only commits.
- When you edit a file, leave the hunks you touched clean (the whole file if it is small).
- Every `# type: ignore` carries a specific error code and a one-line reason.

## Naming & file layout

- One file per concern in a domain app (`models/`, `lib/`, `services/`, `views/`, `serializers/`,
  `filters/`, `permissions/`, `tests/test_*`) — never one file per model or CRUD operation. See
  `CLAUDE.md` → Architecture; copy the shape of `apps/authentication/*/user_profile.py`.
- A new `models/<name>.py` gets a matching `@admin.register(...)` in that app's `admin.py` in the
  same change.

## Imports

Parenthesized when multi-line, one symbol per line, trailing comma; no backslash continuation.
Groups: stdlib, third-party, first-party (`apps.*`), separated by a blank line.

```python
from apps.shared.exceptions import (
    NotFoundError,
    ValidationError,
)
```

## Type hints

- Required on every function / method: all parameters and the return type.
- Nullable values use `X | None` — not `Optional[X]`, not a bare `X = None`.

## Strings

- Double quotes by default; single quotes only to avoid escaping.
- f-strings for interpolation, not `%` or `.format()` — except logging, which keeps lazy `%` args:
  `logger.info("Created id=%s email=%s", profile.id, profile.email)`.

## Long signatures

When a signature exceeds 120 columns, break one parameter per line with a trailing comma, keyword-only
arguments after `*`, and the closing `) -> Type:` on its own line:

```python
def create(
    self,
    *,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
) -> UserProfile:
```

Many positional parameters is a smell — prefer keyword-only arguments or a params object.

## Layers

See `CLAUDE.md` → Architecture for the view / service / serializer / manager split. Beyond what it says:

- **`lib/` is the pure-Python layer.** Auxiliary framework-free classes and functions — calculations,
  parsing, rule evaluation, value objects. No `django.*` imports, no ORM, no I/O, no `interfaces/` calls.
  Takes plain values / dataclasses in and out; the Service fetches via Managers or `interfaces/`, hands
  the data to `lib/`, then persists the result. Reach for it whenever a Service method grows logic
  that isn't itself a query or an external call. Unit-tested only.
- **Repository pattern.** Every query lives as a named QuerySet / Manager method
  (`UserProfile.objects.active()`, `.with_email(email)`) — add one if it is missing. Services and views
  call those methods; they never build a query with raw `.filter(...)` / `.exclude(...)` themselves.
- Serializers are pure mapping: no DB queries inside; fetch and attach the data upstream, then let the
  serializer read already-populated attributes.

`models/<name>.py` holds the QuerySet, Manager, and Model in that order. Name them
`<Model>QuerySet` / `<Model>Manager`; build the manager with `Manager.from_queryset(...)` rather than
re-declaring queryset methods on it. Each method returns the QuerySet so calls chain at the call site
(`Article.objects.published().by_author(user)`). Anything non-trivial — `Q` objects, joins,
`annotate`, `select_related` — belongs in a method here, never inline in a service.

```python
class ArticleQuerySet(models.QuerySet):
    def published(self) -> "ArticleQuerySet":
        return self.filter(status=Article.Status.PUBLISHED)

    def by_author(self, author: "UserProfile") -> "ArticleQuerySet":
        return self.filter(author=author)

    def search(self, term: str) -> "ArticleQuerySet":
        if not term:
            return self
        return self.filter(
            models.Q(title__icontains=term) | models.Q(author__email__icontains=term)
        ).select_related("author")

    def with_comment_counts(self) -> "ArticleQuerySet":
        return self.annotate(comment_count=models.Count("comments"))


class ArticleManager(models.Manager.from_queryset(ArticleQuerySet)):
    pass  # non-query helpers (bulk ops, factory methods) go here


class Article(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft"
        PUBLISHED = "published"

    title: models.CharField = models.CharField(max_length=200)
    author: models.ForeignKey = models.ForeignKey("authentication.UserProfile", on_delete=models.CASCADE)
    status: models.CharField = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)

    objects = ArticleManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Comment(TimeStampedModel):  # child models follow the same trio; QuerySet/Manager omitted here
    article: models.ForeignKey = models.ForeignKey(Article, related_name="comments", on_delete=models.CASCADE)
    body: models.TextField = models.TextField()
```

## Errors

- Services raise the domain exceptions in `apps/shared/exceptions.py` (`ServiceError` and its
  subclasses), never a raw `Model.DoesNotExist` and never an HTTP response.
- Views translate those into responses (catch and re-render with a status, or map to 404 / 403). A view
  never builds an error payload out of a bare ORM exception.

## Comments & docstrings

- Inline comments: one short line, only when the WHY is non-obvious. Never restate the code.
- A short (1–3 line) module or class docstring stating a component's role is welcome — see the
  abstractions in `apps/shared/`. Skip docstrings on self-explanatory methods.

## Baseline

- Line length 120; 4-space indent.
