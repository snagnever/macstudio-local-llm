This repository has one bash script, `wc_report.sh`, that ranks the files of a directory by word count, largest first.

Users report two bugs:
1. A file whose name contains a space is split into two names and never counted.
2. The ranking is wrong when counts have a different number of digits: a file with 10 words is listed after a file with 9 words.

Fix both bugs in `wc_report.sh`. Add one test for each bug to `tests/run_tests.sh`, next to the existing test. Run `bash tests/run_tests.sh` from the repository root and make sure every test passes. Keep the output format `<words> <file name>`. When you are done, reply with one line that says which files you changed.
