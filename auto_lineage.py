from sql_metadata import Parser
import re


class queryparser:
    def __init__(self, sql):
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

        else:
            self.matched = False

    def create_tbl_lineage(self, strict=True):
        assert self.matched is True, "Not a create table query"
        tbls = self.parser.tables
        if strict:
            # only keep temp table and db.tbl
            tbls = [t for t in tbls if "." in t or "#" in t]
        return {self.table: tbls}

    def print_query(self):
        print(self.query)


def create_nested_dict(dictionary, root, added):
    result = {}
    if root in dictionary:
        children = dictionary[root]
        for child in children:
            if child not in dictionary:
                result[child] = ""
            elif child in added:
                result[child] = ""
            else:
                added.add(child)
                result[child] = create_nested_dict(dictionary, child, added)
    return result


# Example usage
original_dict = {
    "#origination2022_init_final": ["#Pre", "#VSA2"],
    "#final_prod": ["edw_caf.l_coll_tv"],
    "#min_app": ["#origination2022_init_final"],
    "#origination_all_final": [
        "#origination2022_init_final",
        "#min_app",
        "#final_prod",
    ],
    "team_caf.orig_all": ["#origination_all_final"],
}


with open("query.sql", "r") as f:
    q = f.read()
qlist = q.split(";")
lineage = {}
seen = []
for query in qlist:
    p = queryparser(query)
    if p.matched:
        if p.table not in seen:
            lineage.update(p.create_tbl_lineage())
            seen.append(p.table)
        else:
            print(f"{p.table} is repetitive, jumped. Query is {p.query}")

root_key = "team_caf.orig_all"
added = set()
converted_dict = {root_key: create_nested_dict(lineage, root_key, added)}
print(converted_dict)
