# Infra steps in the builds

This page describes the purpose of various common steps in builders on
the waterfall and tryservers.

<table>
<colgroup>
<col width="31%" />
<col width="68%" />
</colgroup>
<thead>
<tr class="header">
<th align="left">Step name</th>
<th align="left">Purpose/descripion</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td align="left">find_isolated_tests</td>
<td align="left">Returns a list of *.isolated files together with their SHA1 hashes. Such hash identifies the isolated file tree. It's passed from builder to a tester, or to a swarming job where it is used to reconstruct the file tree (by downloading files from the isolate server). *.isolated files are built during compilation (ninja invokes isolate.py)</td>
</tr>
<tr class="even">
<td align="left">clean_isolated_files</td>
<td align="left">Removes .isolate files from the build directory before compilation (and isolation), to ensure no stale *.isolated are left.</td>
</tr>
<tr class="odd">
<td align="left">cleanup_temp</td>
<td align="left">This step is a hack, which tries to delete portions of the live temp directory based on a variety of hard-coded globs. This is not scalable as people change file names and do not update globs and won't work on Windows, since processes with handles to files make them un-deletable, so there is no way to have this step <em>fail</em>, since there's no way to know if it <em>should</em> be able to delete a given file.</td>
</tr>
</tbody>
</table>


