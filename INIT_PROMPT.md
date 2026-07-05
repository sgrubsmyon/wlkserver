Please start by doing a thorough analysis of the existing codebase. Try to find out what the state of the FastAPI project is: What MySQL table entries can already be created, read, updated and deleted (CRUD)? What is still missing? What parts of business logic contained in `../git/src/org/weltladen_pos/pos/` still need to implemented into the API?

Create an implementation plan (in `concepts/IMPLEMENTATION_PLAN.md`) detailing the steps that still need to be done.

Create a detailed TODO list (in `concepts/TODO.md`) with the missing pieces, in the following format:

```markdown
[x] Already done
[x] Also finished
[ ] This is still missing, see file `../git/src/org/weltladen_bonn/pos/path/to/ClassFile.java`
[ ] Missing as well
[ ] Also missing
```