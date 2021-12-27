import sql
from depdive.code_review import CodeReviewAnalysis
from depdive.repository_diff import ReleaseCommitNotFound
import semver

# q = 'select * from package where ecosystem_id=1 and directory is not null'
# results = sql.execute(q)
# for item in results:
#     id, name = item['id'], item['name']
#     q = 'select * from package_version where package_id=%s'
#     versions = sql.execute(q,(id,))
#     versions = sorted([v['version'] for v in versions], key=semver.VersionInfo.parse)
#     if len(versions) > 1:
#         new = versions[-1]
#         old = versions[-2]
#         q = 'insert into package_update values (null,%s,%s,%s)'
#         sql.execute(q,(id,old,new))
# exit()

q = """select p.name as package, e.name as ecosystem, p.*, pu.id as update_id, pu.*
       from package_update pu
    join package p on pu.package_id = p.id
    join ecosystem e on p.ecosystem_id = e.id
    where pu.id not in
    (select package_update_id from phantom_file
    union
    select package_update_id from no_phantom_file
    union
    select package_update_id from failure
    )
    and directory is not null
    and ecosystem_id = 1
    limit 300"""
results = sql.execute(q)
for item in results:
    package, ecosystem, repository, subdir, old, new, update_id = (
        item["package"],
        item["ecosystem"],
        item["repository"],
        item["directory"],
        item["old"],
        item["new"],
        item["update_id"],
    )
    print(package, ecosystem, repository, subdir, old, new, update_id)
    try:
        ca = CodeReviewAnalysis(ecosystem, package, old, new, repository, subdir)
        ca.run_phantom_analysis()
        if not ca.phantom_files:
            q = "insert into no_phantom_file values(%s)"
            sql.execute(q, (update_id,))
        else:
            for f in ca.phantom_files.keys():
                q = "insert into phantom_file values(%s,%s)"
                sql.execute(q, (update_id, f))

        if not ca.phantom_lines:
            q = "insert into no_phantom_line values(%s)"
            sql.execute(q, (update_id,))
        else:
            for f in ca.phantom_lines.keys():
                for l in ca.phantom_lines[f].keys():
                    q = "insert into phantom_line values(%s,%s,%s,%s,%s)"
                    sql.execute(
                        q, (update_id, f, l, ca.phantom_lines[f][l].additions, ca.phantom_lines[f][l].deletions)
                    )

    except ReleaseCommitNotFound:
        q = "insert into failure values(%s,%s)"
        sql.execute(q, (update_id, ReleaseCommitNotFound.message()))
