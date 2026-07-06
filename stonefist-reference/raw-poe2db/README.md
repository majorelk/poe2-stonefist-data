# raw-poe2db

Local snapshots of PoE2DB glove modifier pages go here, consumed by
`stonefist_import_poe2db_mods.py`.

Expected filenames (one per glove armour class):

```
gloves_str.html
gloves_dex.html
gloves_int.html
gloves_str_dex.html
gloves_str_int.html
gloves_dex_int.html
```

Each file should be the saved HTML of the corresponding page's
`#ModifiersCalc` tab, e.g.:

- https://poe2db.tw/us/Gloves_str#ModifiersCalc
- https://poe2db.tw/us/Gloves_dex#ModifiersCalc
- https://poe2db.tw/us/Gloves_int#ModifiersCalc
- https://poe2db.tw/us/Gloves_str_dex#ModifiersCalc
- https://poe2db.tw/us/Gloves_str_int#ModifiersCalc
- https://poe2db.tw/us/Gloves_dex_int#ModifiersCalc

`.txt` snapshots are also accepted (the importer parses either
extension the same way) in case a page was saved as plain text.

The importer never fetches these automatically. Either save the pages
here yourself, or run the importer once with `--fetch` to have it
download and save snapshots before parsing them.

These are reference snapshots, not perfect ground truth — PoE2DB data
can lag behind game patches.
