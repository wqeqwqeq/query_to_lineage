from sql_metadata import Parser
import re
import json
import yaml


class queryparser:
    def __init__(self, sql, meta={}):
        assert (
            0 <= sql.count(";") <= 1
        ), "Make sure you pass exactly one query. Don't include `;` in comment"

        # (.+?) greedy match one or more
        pattern = r"(CREATE)(.*?)(TABLE)(.+?)(AS\s+\()(.+?)(\)\s*WITH\s+DATA)"
        match = re.search(pattern, sql, re.DOTALL | re.IGNORECASE)

        if match is not None:
            self.table = match.group(4).strip()
            self.query = match.group(6)
            self.parser = Parser(self.query)
            self.matched = True
            self.meta = meta

        else:
            self.matched = False

    def create_tbl_lineage(self, strict=True):
        assert self.matched is True, "Not a create table query"
        tbls = self.parser.tables
        cols = self.meta.get(self.table) if self.meta.get(self.table) else []

        if strict:
            # only keep temp table and db.tbl
            tbls = [{t: {"cols": []}} for t in tbls if "." in t or "#" in t]
        else:
            tbls = [{t: {"cols": []}} for t in tbls]
        return {self.table: {"cols": cols, "subtables": tbls}}

    def print_query(self):
        print(self.query)


def create_nested_dict(lineage, root, added):
    result = {}
    if root.lower() in [k.lower() for k in list(lineage)]:
        result[root] = lineage[root].copy()
        subtables = lineage[root]["subtables"]

        for idx, child in enumerate(subtables):
            key = list(child)[0]
            if key not in lineage:
                pass
            elif key in added:
                pass
            else:
                added.add(key)
                result[root]["subtables"][idx] = create_nested_dict(lineage, key, added)
    return result


with open("query.sql", "r") as f:
    q = f.read()

with open("meta.yml", "r") as f:
    meta = yaml.safe_load(f)
meta = meta["team_caf.orig_all"]

qlist = q.split(";")
lineage = {}
seen = []
for query in qlist:
    p = queryparser(query, meta)
    if p.matched:
        if p.table not in seen:
            lineage.update(p.create_tbl_lineage())
            seen.append(p.table)
        else:
            print(f"{p.table} is repetitive, jumped. Query is {p.query}")

root_key = "team_caf.orig_all"
added = set()
converted_dict = create_nested_dict(lineage, root_key, added)


def dict_handler(json_data):
    result_list = []
    for k, v in json_data.items():
        if isinstance(v, dict):
            result = {}
            result["text"] = k
            result["children"] = dict_handler(v)
            if k == "cols":
                result["state"] = {"opened": False}
            else:
                result["state"] = {"opened": True}
        elif isinstance(v, list):
            result = {}
            result["text"] = k
            result["children"] = []
            if k == "cols":
                result["state"] = {"opened": False}
            else:
                result["state"] = {"opened": True}
            for ele in v:
                if isinstance(ele, dict):
                    result["children"].extend(dict_handler(ele))
                else:
                    result["children"].append({"text": ele})
        else:
            return [{"text": v}]
        result_list.append(result)
    return result_list


final = dict_handler(converted_dict)
with open("final.json", "w") as f:
    f.write(json.dumps(final[0]))
