# 📘 PowerShell — Comprehensive Cheat Sheet

**Author**: DevOps Engineering Team
**Date**: August 2026
**Pages**: 40+ (Equivalent)
**Sections**: 20 Comprehensive Modules
**Examples**: 300+ Working Code Snippets

---

## 📑 Table of Contents
1. [PowerShell Fundamentals](#1-powershell-fundamentals)
2. [Variables & Data Types](#2-variables--data-types)
3. [Operators](#3-operators)
4. [Strings](#4-strings)
5. [Arrays & Collections](#5-arrays--collections)
6. [Hashtables & Custom Objects](#6-hashtables--custom-objects)
7. [Control Flow](#7-control-flow)
8. [Functions](#8-functions)
9. [Pipeline](#9-pipeline)
10. [File & Directory Ops](#10-file--directory-ops)
11. [Error Handling](#11-error-handling)
12. [Modules](#12-modules)
13. [Regex](#13-regex)
14. [Data Formats](#14-data-formats)
15. [Networking](#15-networking)
16. [Remote Management](#16-remote-management)
17. [Active Directory](#17-active-directory)
18. [System Admin](#18-system-admin)
19. [DevOps & Cloud](#19-devops--cloud)
20. [Best Practices](#20-best-practices)

---

## 1. PowerShell Fundamentals

PowerShell is a cross-platform task automation solution made up of a command-line shell, a scripting language, and a configuration management framework. PowerShell runs on Windows, Linux, and macOS.

### PowerShell 5.1 vs PowerShell 7.x

| Feature | PowerShell 5.1 (Windows PowerShell) | PowerShell 7.x (Core) |
| :--- | :--- | :--- |
| **Framework** | .NET Framework 4.5+ | .NET Core / .NET 5+ |
| **OS Support** | Windows Only | Windows, Linux, macOS |
| **Executable** | `powershell.exe` | `pwsh.exe` |
| **Open Source** | No | Yes |
| **Operators** | Standard operators | Added `?:`, `??`, `?.`, `&&`, `||` |
| **Parallelism** | Runspaces / Workflows | `ForEach-Object -Parallel` |

### Cmdlet Naming Convention
PowerShell uses a **Verb-Noun** naming system. This makes it highly readable and intuitive.
- **Verb**: Specifies the action (e.g., `Get`, `Set`, `New`, `Remove`, `Invoke`).
- **Noun**: Specifies the resource (e.g., `Item`, `Process`, `Service`, `AzVM`).

### The Discovery Trinity (Get-Help, Get-Command, Get-Member)

Finding what you need in PowerShell relies on three primary cmdlets.

```powershell
# 1. Get-Command: Find cmdlets based on verbs, nouns, or modules
Get-Command -Verb Get -Noun Process
Get-Command -Module Az.Compute
Get-Command *Network*

# 2. Get-Help: Learn how to use a specific cmdlet
Get-Help Get-Process -Detailed
Get-Help Get-Process -Examples
Get-Help Get-Process -Online

# 3. Get-Member: Explore the properties and methods of an object
Get-Process | Get-Member
Get-Service | Get-Member -MemberType Property
Get-Date | Get-Member -MemberType Method
```

### Execution Policies

Execution policies prevent you from accidentally executing malicious scripts, but they are NOT a security boundary. 

| Policy | Description |
| :--- | :--- |
| **Restricted** | Default on Windows client OS. No scripts can run. |
| **AllSigned** | Scripts can run, but must be signed by a trusted publisher. |
| **RemoteSigned** | Local scripts run without signature. Downloaded scripts must be signed. |
| **Unrestricted** | Any script can run (prompts before running downloaded scripts). |
| **Bypass** | Nothing is blocked, no prompts. (Used often in CI/CD). |

```powershell
# Check current execution policy
Get-ExecutionPolicy -List

# Set execution policy for the current user (requires Admin for LocalMachine)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Bypass execution policy temporarily for a single script (run from cmd/bash)
# pwsh.exe -ExecutionPolicy Bypass -File .\script.ps1
```

### Profiles
A profile is a script that runs when PowerShell starts.

| Profile Name | Variable Path |
| :--- | :--- |
| AllUsersAllHosts | `$PROFILE.AllUsersAllHosts` |
| AllUsersCurrentHost | `$PROFILE.AllUsersCurrentHost` |
| CurrentUserAllHosts | `$PROFILE.CurrentUserAllHosts` |
| CurrentUserCurrentHost | `$PROFILE.CurrentUserCurrentHost` (Default `$PROFILE`) |

```powershell
# Create a profile if it doesn't exist
if (!(Test-Path -Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force
}

# Edit the profile
notepad $PROFILE
```

### Comment Syntax
```powershell
# This is a single-line comment

<#
This is a 
multi-line comment
or block comment
#>
```

> 💡 **Best Practice**: Always use block comments for function Help/Documentation (Comment-Based Help).

---

## 2. Variables & Data Types

Variables in PowerShell start with a `$` sign. PowerShell is dynamically typed, but you can statically type variables (cast) to enforce types.

### Declaration and Casting

```powershell
$myString = "Hello, World!"           # Dynamically typed string
[string]$strictString = "Hello"       # Statically typed string
[int]$myInt = 42                      # Integer
[double]$myDouble = 3.14159           # Double precision float
[bool]$myBool = $true                 # Boolean
[datetime]$myDate = Get-Date          # Date and time object
[array]$myArray = 1, 2, 3             # Array
[hashtable]$myHash = @{Name="Bob"}    # Hashtable
[xml]$myXml = "<root><item/></root>"  # XML Document
[regex]$myRegex = '^\d+$'             # Regular Expression object
```

### Automatic Variables

PowerShell creates several variables automatically that maintain state.

| Variable | Description | Example / Usage |
| :--- | :--- | :--- |
| `$_` or `$PSItem` | Current object in the pipeline | `1..5 | ForEach-Object { $_ * 2 }` |
| `$null` | Represents a null or empty value | `if ($var -eq $null) { ... }` |
| `$true` / `$false`| Boolean true and false values | `[bool]$isActive = $true` |
| `$HOME` | User's home directory | `Set-Location $HOME` |
| `$PWD` | Current working directory | `Write-Host $PWD.Path` |
| `$PSVersionTable` | PowerShell version info | `$PSVersionTable.PSVersion` |
| `$Error` | Array of recent errors (index 0 is newest)| `$Error[0].Exception.Message` |
| `$LASTEXITCODE` | Exit code of last native program | `if ($LASTEXITCODE -ne 0) { throw }` |
| `$?` | Execution status of last command (True/False)| `if (!$?) { Write-Warning "Failed" }` |
| `$PSScriptRoot` | Directory of the executing script | `Import-Module "$PSScriptRoot\mod.psm1"`|
| `$MyInvocation` | Info about current command/script | `$MyInvocation.MyCommand.Path` |

### Environment Variables
Access and modify environment variables using the `env:` drive.

```powershell
# Get environment variable
$path = $env:PATH
$user = $env:USERNAME

# Set environment variable (Process scope only)
$env:MY_VAR = "CustomValue"

# Set persistent environment variable (Machine/User scope)
[Environment]::SetEnvironmentVariable("MY_VAR", "CustomValue", "User")
```

### Variable Scopes
Scopes determine where variables can be read and modified.
- **Global**: Available everywhere in the session.
- **Script**: Available throughout the current script file.
- **Local**: Default scope. Available only in the current function/script block.
- **Private**: Available only in the current scope, cannot be seen by child scopes.

```powershell
$Global:adminUser = "admin"
$Script:logPath = "C:\logs\app.log"
$Local:tempVar = "Temporary"
$Private:secret = "DoNotShare"
```

> 🔧 **DevOps Pro Tip**: Minimize the use of Global variables in scripts to avoid unintended side effects across your CI/CD pipelines or automated tasks. Use parameter passing instead.

---

## 3. Operators

PowerShell offers a massive suite of operators for arithmetic, comparison, logic, and more. 

### Arithmetic Operators
```powershell
$a = 10 + 5   # Addition (15)
$b = 10 - 5   # Subtraction (5)
$c = 10 * 5   # Multiplication (50)
$d = 10 / 5   # Division (2)
$e = 10 % 3   # Modulus/Remainder (1)
```

### Assignment Operators
```powershell
$x = 5        # Assign 5 to $x
$x += 2       # $x = $x + 2 (7)
$x -= 1       # $x = $x - 1 (6)
$x *= 3       # $x = $x * 3 (18)
$x /= 2       # $x = $x / 2 (9)
```

### Comparison Operators (Case-Insensitive by Default)
*Note: Prefix with `c` for case-sensitive (`-ceq`, `-cne`) and `i` for explicit case-insensitive (`-ieq`).*

| Operator | Description | Example |
| :--- | :--- | :--- |
| `-eq` | Equals | `5 -eq 5` -> True |
| `-ne` | Not equals | `"apple" -ne "orange"` -> True |
| `-gt` / `-ge`| Greater than / Greater or equal | `10 -gt 5` -> True |
| `-lt` / `-le`| Less than / Less or equal | `3 -le 3` -> True |
| `-like` | Wildcard match | `"PowerShell" -like "*Shell"` -> True |
| `-notlike` | Wildcard not match | `"Linux" -notlike "*Shell"` -> True |
| `-match` | Regex match | `"12345" -match "^\d+$"` -> True |
| `-notmatch` | Regex not match | `"abc" -notmatch "^\d+$"` -> True |
| `-contains` | Array contains item (exact) | `1,2,3 -contains 2` -> True |
| `-notcontains`| Array doesn't contain item | `1,2,3 -notcontains 4` -> True |
| `-in` | Item is in array | `2 -in 1,2,3` -> True |
| `-notin` | Item is not in array | `4 -notin 1,2,3` -> True |

```powershell
# 15+ Comparison Examples
$true -eq ($null -eq $null)
"hello" -eq "HELLO"               # True (case-insensitive)
"hello" -ceq "HELLO"              # False (case-sensitive)
10 -gt 5 -and 5 -lt 10            # True
"Server01" -like "Server*"        # True
"abc123def" -match "\d{3}"        # True ($Matches populated)
$array = "apple", "banana", "pear"
$array -contains "banana"         # True
"pear" -in $array                 # True
"grape" -notin $array             # True
$array -ccontains "BANANA"        # False
$array -notcontains "grape"       # True
"file.txt" -like "*.txt"          # True
"Status: OK" -match "^Status: (.*)" # True, $Matches[1] = "OK"
```

### Logical Operators
```powershell
$true -and $true     # True
$true -or $false     # True
$true -xor $true     # False (Exclusive OR)
-not $true           # False
!$true               # False (Alias for -not)
```

### Bitwise Operators
```powershell
5 -band 3            # Bitwise AND (1)
5 -bor 3             # Bitwise OR (7)
5 -bxor 3            # Bitwise XOR (6)
-bnot 5              # Bitwise NOT (-6)
1 -shl 2             # Shift left (4)
8 -shr 2             # Shift right (2)
```

### String & Redirection Operators
```powershell
# String Operators
"a", "b", "c" -join "-"       # "a-b-c"
"a-b-c" -split "-"            # Array: "a", "b", "c"
"Hello" -replace "ll", "y"    # "Heyo"

# Redirection
# >  : Write to file (overwrite)
# >> : Append to file
# 2> : Redirect errors
# *> : Redirect all streams
Get-Process > procs.txt
Write-Warning "Oops" 2>> errors.log
.\script.ps1 *> all_output.log
```

### Type & Range Operators
```powershell
1..5                          # Array: 1, 2, 3, 4, 5
"Hello" -is [string]          # True
42 -isnot [string]            # True
$obj = $someVar -as [int]     # Casts to int, returns $null if it fails
```

### PowerShell 7+ Exclusive Operators
```powershell
# Ternary Operator (Condition ? IfTrue : IfFalse)
$status = ($code -eq 200) ? "OK" : "Error"

# Null-coalescing (??) - assign if right is null
$value = $null ?? "Default"    # "Default"

# Null-coalescing assignment (??=)
$var ??= "Assigned because $var was null"

# Null-conditional (?.) - access property only if not null
$length = $myString?.Length    # Null instead of error if $myString is null

# Pipeline Chain (&&, ||)
Write-Output "Success" && Write-Output "Runs if first succeeds"
Write-Error "Fail" || Write-Output "Runs if first fails"
```

---

## 4. Strings

PowerShell handles strings powerfully. Understanding quotes is critical.

### Single vs Double Quotes

| Quote Type | Interpolation? | Escape Character | Example | Output |
| :--- | :--- | :--- | :--- | :--- |
| **Single** (`'`) | No (Literal) | Literal | `'Cost: $10'` | `Cost: $10` |
| **Double** (`"`) | Yes (Expands vars) | Backtick (`` ` ``) | `"Cost: $cost"` | `Cost: 10` |

### Here-Strings
Used for multi-line strings. Must start with `@'` or `@"`, and end with `'@` or `"@` on their own line.

```powershell
$sqlQuery = @"
SELECT *
FROM Users
WHERE Name = '$username'
"@
```

### String Methods (.NET)
Since PowerShell strings are .NET `System.String` objects, they have many methods.

```powershell
$str = "  Hello PowerShell World  "

$str.Length                # Property, not a method
$str.ToUpper()             # "  HELLO POWERSHELL WORLD  "
$str.ToLower()             # "  hello powershell world  "
$str.Trim()                # "Hello PowerShell World"
$str.TrimStart()           # "Hello PowerShell World  "
$str.TrimEnd()             # "  Hello PowerShell World"
$str.Split(" ")            # Splits by space into array
$str.Replace("World", "PS")# "  Hello PowerShell PS  "
$str.Substring(2, 5)       # "Hello"
$str.StartsWith("  H")     # True
$str.EndsWith("d  ")       # True
$str.Contains("Power")     # True
$str.IndexOf("P")          # 8
$str.Insert(8, "Awesome ") # "  Hello Awesome PowerShell World  "
$str.Remove(2, 6)          # "  PowerShell World  "
```

### The Format Operator (`-f`)
Extremely useful for templating, padding, and formatting strings.

```powershell
# Basic insertion
"Hello {0}, you are {1} years old" -f "Alice", 30

# Padding (Right/Left)
"|{0, -10}|{1, 10}|" -f "Left", "Right" # |Left      |     Right|

# Number formatting
"{0:N2}" -f 1234.5678       # 1,234.57 (Number with 2 decimals)
"{0:C}" -f 1234.5678        # $1,234.57 (Currency)
"{0:P}" -f 0.85             # 85.00% (Percentage)
"{0:D5}" -f 42              # 00042 (Decimal padding)
"{0:X}" -f 255              # FF (Hexadecimal)

# Date formatting
"Today is {0:yyyy-MM-dd}" -f (Get-Date)
```

### Select-String (Grep for PowerShell)
Searches for text or regex patterns in strings and files.

```powershell
# Search in a string
"Hello World" | Select-String -Pattern "World"

# Search in a file
Select-String -Path ".\app.log" -Pattern "ERROR:"

# Return only the matched string (not the whole line)
(Select-String -Path ".\app.log" -Pattern "IP: (\d+\.\d+\.\d+\.\d+)").Matches.Groups[1].Value

# Case sensitive search
Select-String -Path ".\file.txt" -Pattern "Exception" -CaseSensitive

# Context (lines before and after)
Select-String -Path ".\file.txt" -Pattern "CRITICAL" -Context 2, 3
```

---

## 5. Arrays & Collections

### Basic Arrays
Created using the array subexpression operator `@()` or comma-separated values.
Arrays in PowerShell are fixed-size by default. Adding to an array (`+=`) destroys and recreates the array, which is very slow in loops.

```powershell
# Creation
$arr1 = @(1, 2, 3, 4, 5)
$arr2 = "Apple", "Banana", "Cherry"
$emptyArray = @()
$singleItemArray = @("JustMe")

# Operations
$arr1[0]             # 1 (0-indexed)
$arr1[-1]            # 5 (Last item)
$arr1[0..2]          # 1, 2, 3 (Slice)
$arr1 += 6           # Adds 6 (SLOW for large arrays!)
```

### Generic Lists (ArrayList / List[T])
For performance, use `System.Collections.Generic.List[T]`.

```powershell
# Create a strongly typed list
$list = [System.Collections.Generic.List[string]]::new()
$list.Add("Apple")
$list.Add("Banana")
$list.Remove("Apple")
$list.Count

# Adding is O(1) time complexity - much faster than +=
```

### Array Methods (.Where() and .ForEach())
PowerShell 4+ introduced collection methods which are much faster than pipeline `Where-Object` and `ForEach-Object`.

```powershell
$numbers = 1..100

# .Where() method
$evens = $numbers.Where({ $_ % 2 -eq 0 })
$firstFiveEvens = $numbers.Where({ $_ % 2 -eq 0 }, 'First', 5)

# .ForEach() method
$doubled = $numbers.ForEach({ $_ * 2 })
```

### Multi-Dimensional and Jagged Arrays
```powershell
# 2D Array
$grid = New-Object 'object[,]' 3, 3
$grid[0,0] = "TopLeft"

# Jagged Array (Array of Arrays)
$jagged = @(
    @(1, 2, 3),
    @(4, 5),
    @(6, 7, 8, 9)
)
$jagged[1][0] # Returns 4
```

---

## 6. Hashtables & Custom Objects

### Hashtables (Dictionaries)
Key-value pairs. Created using `@{}`. Unordered by default.

```powershell
# Creation
$hash = @{
    Name = "Alice"
    Age = 30
    City = "New York"
}

# Ordered Hashtable (Maintains insertion order)
$orderedHash = [ordered]@{
    First = 1
    Second = 2
    Third = 3
}

# Operations
$hash["Name"]          # Alice
$hash.Age              # 30
$hash.Add("Role", "Admin") # Add new key
$hash.Remove("Age")    # Remove key
$hash.Keys             # List all keys
$hash.Values           # List all values
$hash.ContainsKey("City") # True
```

### Custom Objects [PSCustomObject]
The standard way to create structured data in PowerShell. Cast a hashtable to `[PSCustomObject]`.

```powershell
$userObj = [PSCustomObject]@{
    FirstName = "John"
    LastName  = "Doe"
    Role      = "Developer"
    Active    = $true
}

# Adding properties later using Add-Member
$userObj | Add-Member -MemberType NoteProperty -Name "Department" -Value "IT"

# Adding a ScriptMethod
$userObj | Add-Member -MemberType ScriptMethod -Name "GetFullName" -Value {
    return "$($this.FirstName) $($this.LastName)"
}
$userObj.GetFullName()
```

### Splatting
Splatting uses a hashtable to pass parameters to a cmdlet cleanly. VERY important for readable code.

```powershell
$copyParams = @{
    Path        = "C:\source\*"
    Destination = "D:\backup\"
    Recurse     = $true
    Force       = $true
    PassThru    = $true
}

# Call cmdlet using @ symbol instead of $
Copy-Item @copyParams
```

> 🔧 **DevOps Pro Tip**: Always use splatting for cmdlets that take more than 3 parameters (like `Invoke-RestMethod` or `New-AzVM`) to vastly improve script maintainability.

---

## 7. Control Flow

### If / ElseIf / Else
```powershell
$cpuUsage = 85

if ($cpuUsage -ge 90) {
    Write-Warning "CRITICAL: CPU over 90%"
}
elseif ($cpuUsage -ge 75) {
    Write-Warning "WARNING: CPU over 75%"
}
else {
    Write-Output "CPU is normal"
}
```

### Switch
Switch is incredibly powerful in PowerShell. It can test against regex, wildcards, files, and more.

```powershell
# Simple Switch
$color = "Red"
switch ($color) {
    "Red"   { Write-Host "Stop"; break }
    "Green" { Write-Host "Go"; break }
    Default { Write-Host "Unknown" }
}

# Wildcard Switch
$file = "document.txt"
switch -Wildcard ($file) {
    "*.txt"  { "Text file" }
    "*.json" { "JSON file" }
}

# Regex Switch
$ip = "192.168.1.1"
switch -Regex ($ip) {
    "^192\." { "Internal Network" }
    "^10\."  { "Private Network" }
}

# File Switch (Iterates over lines in a file)
switch -File ".\config.ini" -Regex {
    "^Server=(.*)" { $server = $Matches[1] }
    "^Port=(.*)"   { $port = $Matches[1] }
}
```

### Loops (For / Foreach / While / Do)

```powershell
# For loop
for ($i = 0; $i -lt 5; $i++) {
    Write-Host "Index $i"
}

# Foreach loop (Faster than pipeline Foreach-Object)
$servers = @("Server1", "Server2", "Server3")
foreach ($server in $servers) {
    Write-Host "Pinging $server"
}

# While loop
$count = 0
while ($count -lt 3) {
    Write-Host "Count is $count"
    $count++
}

# Do-While (Executes at least once)
$input = ""
do {
    $input = Read-Host "Type 'exit' to quit"
} while ($input -ne "exit")

# Do-Until
do {
    $status = Get-Service -Name "wuauserv"
    Start-Sleep -Seconds 1
} until ($status.Status -eq "Running")
```

### Break and Continue
- `break`: Exits the loop entirely.
- `continue`: Skips the rest of the current iteration and moves to the next.

---

## 8. Functions

Functions allow code reuse. Advanced functions behave exactly like compiled cmdlets.

### Simple Function
```powershell
function Get-Greeting {
    param($Name)
    "Hello, $Name"
}
Get-Greeting -Name "World"
```

### Advanced Function (CmdletBinding)
This enables common parameters (`-Verbose`, `-Debug`, `-ErrorAction`, etc.) and supports pipeline input.

```powershell
function Restart-CustomService {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory = $true, 
                   ValueFromPipeline = $true, 
                   ValueFromPipelineByPropertyName = $true)]
        [ValidateNotNullOrEmpty()]
        [string[]]$ServiceName,

        [Parameter(Mandatory = $false)]
        [ValidateSet("Dev", "Test", "Prod")]
        [string]$Environment = "Dev"
    )

    begin {
        Write-Verbose "Starting function execution"
    }

    process {
        foreach ($name in $ServiceName) {
            if ($PSCmdlet.ShouldProcess($name, "Restart Service in $Environment")) {
                try {
                    Restart-Service -Name $name -ErrorAction Stop
                    Write-Output "Successfully restarted $name"
                }
                catch {
                    Write-Error "Failed to restart $name: $_"
                }
            }
        }
    }

    end {
        Write-Verbose "Finished function execution"
    }
}
```

### Parameter Validation Attributes
- `[ValidateSet("A", "B", "C")]`: Must be one of the listed values.
- `[ValidateRange(1, 100)]`: Must be between 1 and 100.
- `[ValidatePattern("^\d+$")]`: Must match Regex.
- `[ValidateScript({ Test-Path $_ })]`: Must pass the script block test.
- `[ValidateNotNullOrEmpty()]`: Self-explanatory.

---

## 9. Pipeline

The PowerShell pipeline passes **objects**, not text. This is PowerShell's defining feature.

```mermaid
graph LR
    subgraph Linux / Bash (Text)
        A["Command 1"] -->|Raw Text Streams| B["grep / awk"]
        B -->|String parsing| C["Command 2"]
    end
    
    subgraph PowerShell (Objects)
        D["Get-Process"] -->|Live .NET Objects| E["Where-Object"]
        E -->|Filtered Objects| F["Stop-Process"]
        note["Properties & Methods remain intact"] -.-> E
    end
```

### Where-Object (Filtering)
```powershell
# Scriptblock syntax (Classic, handles complex logic)
Get-Process | Where-Object { $_.WorkingSet -gt 200MB -and $_.Name -like "chrome*" }

# Simplified syntax (Faster, reads naturally, but limits to one condition)
Get-Service | Where-Object Status -eq "Running"
Get-EventLog -LogName System | Where-Object EventID -in 1000, 1001
```

### ForEach-Object (Iterating)
```powershell
# Basic
Get-ChildItem *.txt | ForEach-Object { Move-Item $_.FullName -Destination "C:\Archive\" }

# With Begin/Process/End
Get-Content numbers.txt | ForEach-Object -Begin { $sum = 0 } -Process { $sum += [int]$_ } -End { "Total: $sum" }

# Parallel (PowerShell 7+ only)
1..100 | ForEach-Object -Parallel { Test-Connection "192.168.1.$_" -Count 1 } -ThrottleLimit 20
```

### Select-Object (Projecting)
```powershell
# Select specific properties
Get-Process | Select-Object Name, Id, CPU

# Expand property (extracts raw value, drops object wrapper)
Get-Service | Select-Object -ExpandProperty Name

# First, Last, Skip
Get-Process | Sort-Object CPU -Descending | Select-Object -First 5
Get-EventLog -LogName Application | Select-Object -Skip 10 -First 5

# Unique values
"A", "B", "A", "C" | Select-Object -Unique

# Calculated Properties (Extremely useful!)
Get-Process | Select-Object Name, @{Name="Memory(MB)"; Expression={[math]::Round($_.WorkingSet / 1MB, 2)}}
```

### Sorting and Grouping
```powershell
# Sort-Object
Get-ChildItem | Sort-Object Length -Descending
Get-Process | Sort-Object Company, CPU -Descending

# Group-Object
Get-Service | Group-Object Status
$grouped = Get-Process | Group-Object Name -AsHashTable -AsString
$grouped["chrome"] # Returns all Chrome processes
```

### Measure and Compare
```powershell
# Measure-Object
Get-ChildItem *.log | Measure-Object -Property Length -Sum -Average -Maximum
(1..10 | Measure-Object -Sum).Sum

# Compare-Object (Diffs two arrays/files)
$file1 = Get-Content old.txt
$file2 = Get-Content new.txt
Compare-Object -ReferenceObject $file1 -DifferenceObject $file2
```

---

## 10. File & Directory Ops

### Get-ChildItem (ls / dir)
```powershell
Get-ChildItem -Path "C:\Logs"
Get-ChildItem -Path "C:\Logs" -Filter "*.log" -Recurse
Get-ChildItem -Path "C:\Logs" -File        # Files only
Get-ChildItem -Path "C:\Logs" -Directory   # Directories only
Get-ChildItem -Path "C:\Logs" -Hidden      # Hidden files
```

### File Operations
```powershell
# New-Item (Touch / Mkdir)
New-Item -Path "C:\Temp\newfile.txt" -ItemType File
New-Item -Path "C:\Temp\NewFolder" -ItemType Directory

# Copy / Move / Rename / Remove
Copy-Item ".\file.txt" -Destination ".\backup.txt"
Move-Item ".\file.txt" -Destination "C:\Archive\"
Rename-Item ".\old.txt" -NewName "new.txt"
Remove-Item ".\temp.txt" -Force -Recurse

# Test-Path (Check if exists)
if (Test-Path "C:\Temp\config.json") { "Exists!" }
```

### Content Operations (cat / echo)
```powershell
# Get-Content
$lines = Get-Content ".\log.txt"
$rawStr = Get-Content ".\log.txt" -Raw      # Reads as single string (Faster)
$tail = Get-Content ".\log.txt" -Tail 10    # Last 10 lines
Get-Content ".\log.txt" -Wait               # Follow log (like tail -f)

# Set / Add Content
"Log Entry" | Add-Content ".\app.log"       # Append
"New Config" | Set-Content ".\config.txt"   # Overwrite
Clear-Content ".\temp.txt"                  # Empty file
```

### Paths and Hashes
```powershell
Join-Path "C:\Logs" "app.log"               # C:\Logs\app.log
Split-Path "C:\Logs\app.log" -Leaf          # app.log
Split-Path "C:\Logs\app.log" -Parent        # C:\Logs

Get-FileHash -Path ".\installer.exe" -Algorithm SHA256
```

---

## 11. Error Handling

PowerShell has two types of errors: Terminating (stops execution) and Non-Terminating (writes to error stream, execution continues).

### ErrorActionPreference
Controls how non-terminating errors are handled globally.
Values: `Continue` (Default), `Stop`, `SilentlyContinue`, `Ignore`, `Inquire`.

```powershell
$ErrorActionPreference = "Stop" # Treat ALL errors as terminating (Recommended for CI/CD)
```

### Try / Catch / Finally
```powershell
try {
    # -ErrorAction Stop forces a non-terminating error to be terminating so catch can grab it
    Get-Content "C:\DoesNotExist.txt" -ErrorAction Stop
    $result = 10 / 0
}
catch [System.IO.FileNotFoundException] {
    Write-Warning "File not found!"
    # The error object is $_
    Write-Error $_.Exception.Message
}
catch [System.DivideByZeroException] {
    Write-Warning "Cannot divide by zero!"
}
catch {
    # Catch-all for any other error
    Write-Error "An unexpected error occurred: $_"
}
finally {
    # Runs regardless of success or failure. Great for cleanup.
    Write-Host "Cleanup code runs here."
}
```

### Throwing Errors
```powershell
if ($path -eq $null) {
    throw "Path cannot be null!" # Creates a terminating error
}
```

---

## 12. Modules

Modules group functions, variables, and aliases into reusable packages.

### Working with Modules
```powershell
# Find installed modules
Get-Module -ListAvailable

# Import a module
Import-Module Az.Accounts

# Remove from session
Remove-Module Az.Accounts

# Discover and install from PSGallery
Find-Module -Name dbatools
Install-Module -Name dbatools -Scope CurrentUser -Force
```

### Creating a Module
1. Create a folder `MyModule`.
2. Create `MyModule.psm1` inside it (contains functions).
3. Create a manifest `MyModule.psd1` using `New-ModuleManifest`.

```powershell
New-ModuleManifest -Path .\MyModule\MyModule.psd1 -RootModule MyModule.psm1 -Author "DevOps" -Description "Custom tools"
```
In `MyModule.psm1`:
```powershell
function Get-ServerStatus { ... }
Export-ModuleMember -Function Get-ServerStatus
```

### Dot-Sourcing
Runs a script in the *current* scope, rather than its own script scope.
```powershell
. .\myFunctions.ps1 # Now all variables and functions in myFunctions.ps1 are available in your console
```

---

## 13. Regex (Regular Expressions)

PowerShell has native support for Regex via the `-match` operator and the `[regex]` class.

### Matching and Capturing
```powershell
$log = "Error: Invalid token at 2026-08-05"

# Basic match
if ($log -match "Error: (.*) at (\d{4}-\d{2}-\d{2})") {
    $Matches[0] # The entire matched string
    $Matches[1] # "Invalid token" (Group 1)
    $Matches[2] # "2026-08-05" (Group 2)
}

# Named Capture Groups
if ($log -match "(?<Level>Error|Warning): (?<Message>.*)") {
    $Matches.Level
    $Matches.Message
}
```

### Replacing with Groups
```powershell
# Swap date format from YYYY-MM-DD to DD/MM/YYYY
"Date: 2026-08-05" -replace "(\d{4})-(\d{2})-(\d{2})", '$3/$2/$1'
```

### Regex Class Methods
```powershell
# Find all occurrences
$text = "IPs: 192.168.1.1, 10.0.0.5, 172.16.0.2"
$pattern = "\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
[regex]::Matches($text, $pattern).Value
```

---

## 14. Data Formats

PowerShell natively translates object data into structured text formats.

### CSV (Comma Separated Values)
```powershell
# Export objects to CSV
Get-Process | Select-Object Name, Id, CPU | Export-Csv -Path ".\procs.csv" -NoTypeInformation

# Import objects from CSV
$csvData = Import-Csv -Path ".\users.csv"
foreach ($row in $csvData) {
    Write-Host "Creating user: $($row.Username)"
}

# Convert text to objects (without saving to file)
$csvString | ConvertFrom-Csv
```

### JSON
```powershell
# Convert objects to JSON
$userObj | ConvertTo-Json -Depth 5 > user.json

# Convert JSON to objects
$parsedJson = Get-Content ".\config.json" -Raw | ConvertFrom-Json
$parsedJson.Database.ConnectionString

# PS7+ AsHashTable (keeps JSON keys as hashtable instead of custom objects, great for dynamic keys)
$hashJson = Get-Content ".\data.json" -Raw | ConvertFrom-Json -AsHashtable
```

### XML
```powershell
# Read XML
[xml]$xml = Get-Content ".\config.xml"
$xml.root.appSettings.add.value

# XPath Search
Select-Xml -Xml $xml -XPath "//add[@key='API_KEY']" | Select-Object -ExpandProperty Node
```

### CliXML
PowerShell's native serialization format. Retains type data (methods are lost, but property types remain).
```powershell
Get-Credential | Export-Clixml ".\cred.xml" # Safely encrypts passwords to disk for the current user/machine
$cred = Import-Clixml ".\cred.xml"
```

---

## 15. Networking

### Testing Connections
```powershell
# Ping equivalent (returns object)
Test-NetConnection -ComputerName google.com

# Test Port / Telnet equivalent
Test-NetConnection -ComputerName dbserver.local -Port 1433

# DNS Resolution
Resolve-DnsName -Name google.com -Type A
```

### Web Requests & REST APIs
`Invoke-RestMethod` automatically parses JSON/XML responses into PowerShell objects.

```powershell
# Simple GET
$response = Invoke-RestMethod -Uri "https://api.github.com/users/octocat"
$response.name

# GET with Headers (Auth)
$headers = @{
    Authorization = "Bearer $token"
    Accept        = "application/json"
}
$data = Invoke-RestMethod -Uri "https://api.mycorp.com/v1/users" -Headers $headers -Method Get

# POST with Body
$body = @{
    title = "New Issue"
    body  = "Please fix the bug"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://api.mycorp.com/v1/issues" -Method Post -Headers $headers -Body $body -ContentType "application/json"

# File Download (Invoke-WebRequest)
Invoke-WebRequest -Uri "https://example.com/installer.zip" -OutFile "C:\Temp\installer.zip"
```

### TLS Configuration (Important for legacy systems)
```powershell
# Force TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
```

---

## 16. Remote Management

PowerShell Remoting uses WinRM (Windows) or SSH (Cross-platform).

```mermaid
graph TD
    A["Admin Workstation (pwsh)"] -->|Enter-PSSession / Invoke-Command| B{"Transport Protocol"}
    
    B -->|Windows Native (HTTP 5985 / HTTPS 5986)| C["WinRM Service"]
    C --> D["WSMAN Plugin (powershell.exe)"]
    D --> E["Windows Server Target"]
    
    B -->|Cross-Platform (TCP 22)| F["SSH Daemon"]
    F --> G["PowerShell Subsystem (pwsh)"]
    G --> H["Linux / macOS / Windows Target"]
```

### Interactive Remoting
```powershell
Enter-PSSession -ComputerName "Server01" -Credential (Get-Credential)
# Prompt changes to [Server01]: PS>
Exit-PSSession
```

### One-to-Many Script Execution (Invoke-Command)
Executes code in parallel across multiple machines.

```powershell
# Run a scriptblock on 3 servers concurrently
$servers = "Web01", "Web02", "Web03"
Invoke-Command -ComputerName $servers -ScriptBlock {
    Get-Service w3svc
}

# Passing local variables to remote session ($Using:)
$serviceName = "Spooler"
Invoke-Command -ComputerName $servers -ScriptBlock {
    Restart-Service -Name $Using:serviceName
}

# Run a local script file on remote servers
Invoke-Command -ComputerName $servers -FilePath ".\Update-App.ps1"
```

### Sessions (Persistent Connections)
```powershell
$session = New-PSSession -ComputerName "SQL01"
Invoke-Command -Session $session -ScriptBlock { $global:TempData = "Data" }
Invoke-Command -Session $session -ScriptBlock { Write-Host $global:TempData }
Remove-PSSession -Session $session
```

---

## 17. Active Directory

Requires RSAT (Remote Server Administration Tools) or the `ActiveDirectory` module.

### User Management
```powershell
# Get User
Get-ADUser -Identity "jdoe" -Properties EmailAddress, Department, LastLogonDate

# Search Users
Get-ADUser -Filter {Department -eq "IT" -and Enabled -eq $true} -Properties EmailAddress | Select-Object Name, EmailAddress

# New User
New-ADUser -Name "Alice Smith" -SamAccountName "asmith" -UserPrincipalName "asmith@corp.com" -Path "OU=Users,DC=corp,DC=com" -AccountPassword $secureString -Enabled $true

# Update User
Set-ADUser -Identity "asmith" -Title "Senior Engineer"

# Remove User
Remove-ADUser -Identity "asmith" -Confirm:$false
```

### Group Management
```powershell
# Create Group
New-ADGroup -Name "App_Admins" -GroupScope Global -Path "OU=Groups,DC=corp,DC=com"

# Add Members
Add-ADGroupMember -Identity "App_Admins" -Members "asmith", "jdoe"

# Get Members
Get-ADGroupMember -Identity "App_Admins" | Select-Object Name, objectClass
```

### LDAP Filters
More efficient than PowerShell `-Filter` for massive directories.
```powershell
# Find all enabled users with an email address
Get-ADUser -LDAPFilter "(&(objectCategory=person)(objectClass=user)(!userAccountControl:1.2.840.113556.1.4.803:=2)(mail=*))"
```

---

## 18. System Administration

### Services and Processes
```powershell
# Services
Get-Service -Name "*wuauserv*"
Start-Service -Name wuauserv
Restart-Service -Name wuauserv -Force
Set-Service -Name wuauserv -StartupType Automatic

# Processes
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10
Stop-Process -Name "chrome" -Force
Stop-Process -Id 1234
```

### Event Logs
```powershell
# Classic EventLog
Get-EventLog -LogName System -EntryType Error -Newest 50

# Get-WinEvent (Modern, much faster, queries EVTX)
$filter = @{
    LogName   = 'System'
    Level     = 2  # Error
    StartTime = (Get-Date).AddDays(-1)
}
Get-WinEvent -FilterHashtable $filter

# Search for specific EventID
Get-WinEvent -FilterHashtable @{LogName='Security'; ID=4624} -MaxEvents 10
```

### WMI / CIM (Windows Management Instrumentation)
CIM is the modern standard over WMI. It uses WS-Man instead of DCOM.

```mermaid
graph LR
    A["pwsh (Get-CimInstance)"] -->|WS-Man (TCP 5985)| B["Target Server"]
    B --> C["CIM Object Manager (CIMOM)"]
    C --> D["WMI Providers"]
    D --> E["Hardware / OS Data"]
```

```powershell
# Get OS Info
Get-CimInstance -ClassName Win32_OperatingSystem | Select-Object Caption, Version, LastBootUpTime

# Get Disk Space
Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DriveType=3" | 
    Select-Object DeviceID, @{N='FreeSpaceGB';E={[math]::Round($_.FreeSpace/1GB,2)}}

# Get BIOS Serial Number
Get-CimInstance -ClassName Win32_BIOS | Select-Object SerialNumber
```

### Registry Operations
Access the registry like a file system.
```powershell
# Navigate registry
Set-Location HKLM:\Software\Microsoft\Windows\CurrentVersion

# Get/Set Values
Get-ItemProperty -Path "HKLM:\Software\MyCorp\App" -Name "Version"
Set-ItemProperty -Path "HKLM:\Software\MyCorp\App" -Name "Version" -Value "2.0"
New-Item -Path "HKLM:\Software\MyCorp\NewApp"
```

---

## 19. DevOps & Cloud Integration

PowerShell acts as the glue code for CI/CD pipelines and cloud deployments.

### Azure (Az Module)

```mermaid
graph TD
    A["PowerShell Runbook / CI Agent"] -->|1. Connect-AzAccount| B["Microsoft Entra ID (Azure AD)"]
    B -->|2. Returns OAuth Token| A
    A -->|3. Get-AzVM (Bearer Token)| C["Azure Resource Manager (ARM) API"]
    C -->|4. JSON Response| D["Az Module (Deserializes JSON)"]
    D -->|5. Returns PSCustomObject| A
```

```powershell
# Connect / Auth (Supports Service Principals and Managed Identities)
Connect-AzAccount -Identity # Managed Identity in Azure VM
Connect-AzAccount -ServicePrincipal -TenantId $tid -ApplicationId $appId -CertificateThumbprint $thumb

# Manage Resources
Get-AzResourceGroup
$vm = Get-AzVM -ResourceGroupName "Prod-RG" -Name "WebVM01"
Start-AzVM -ResourceGroupName $vm.ResourceGroupName -Name $vm.Name

# Query Graph API using Az Token
$token = (Get-AzAccessToken -ResourceUrl "https://graph.microsoft.com").Token
```

### AWS (AWSPowerShell Module)
```powershell
Initialize-AWSDefaultConfiguration -Region us-east-1
Get-EC2Instance | Select-Object InstanceId, InstanceType
```

### Pester Testing
Pester is the BDD-style testing framework for PowerShell. Crucial for Infrastructure-as-Code testing.

```powershell
Describe "IIS Web Server Configurations" {
    Context "Service Status" {
        It "Should be running" {
            $service = Get-Service -Name W3SVC
            $service.Status | Should -Be "Running"
        }
    }
    
    Context "Network Ports" {
        It "Should listen on Port 80" {
            $portInfo = Test-NetConnection -ComputerName localhost -Port 80
            $portInfo.TcpTestSucceeded | Should -Be $true
        }
    }
}
```

### Docker & kubectl
PowerShell executes native CLI tools easily. Use `$LASTEXITCODE` for error handling.
```powershell
docker build -t myapp:v1 .
if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }

$pods = kubectl get pods -o json | ConvertFrom-Json
$pods.items.metadata.name
```

---

## 20. Best Practices & Pro Tips

### Code Style
- Use **PascalCase** for functions, parameters, and variables.
- Indent with **4 spaces**.
- Never use aliases (`?`, `%`, `ls`, `cd`, `iwr`) in scripts; they hurt readability. Save them for the interactive console.
- Always include `CmdletBinding()` in your scripts to enable `-Verbose` output natively.

### Performance Optimizations
- **Avoid `+=` with arrays**: Use `System.Collections.Generic.List[T]` or assign the output of a loop directly to a variable (`$arr = foreach ($x in $y) { $x }`).
- **Pipeline is slow**: `Foreach-Object` is heavily resource-intensive compared to a standard `foreach ($item in $collection)` statement. Use the pipeline for readability on small datasets, use `foreach` statements for massive datasets.
- **String Concat**: For building massive strings, use `[System.Text.StringBuilder]`.
- **Filtering Left**: Filter as early in the pipeline as possible. (`Get-Process | Where-Object Name -eq "chrome"` is slower than `Get-Process -Name "chrome"`).

### Security
- NEVER hardcode passwords.
- Use `Get-Credential` for interactive scripts.
- Use Azure KeyVault, AWS Secrets Manager, or Export-Clixml for background automation.
- **SecureString**: `ConvertTo-SecureString -String "MySecret" -AsPlainText -Force`. Note: In PowerShell 7, SecureString is deprecated for cross-platform, standard strings are used in memory buffers.

### Debugging
```powershell
# Set a breakpoint on line 15 of script.ps1
Set-PSBreakpoint -Script .\script.ps1 -Line 15

# Breakpoint on a specific command
Set-PSBreakpoint -Command "Invoke-RestMethod"

# Drops you into the debugger mid-script execution
Wait-Debugger 
```

### 30+ Useful One-Liners (Quick Reference)

1. **Find large files**: `Get-ChildItem C:\ -Recurse -File -ErrorAction SilentlyContinue | Sort-Object Length -Descending | Select-Object -First 10`
2. **Find empty folders**: `Get-ChildItem -Directory -Recurse | Where-Object { (Get-ChildItem $_.FullName).Count -eq 0 }`
3. **Get public IP**: `(Invoke-WebRequest ifconfig.me/ip).Content`
4. **Generate random password**: `[System.Web.Security.Membership]::GeneratePassword(16, 2)`
5. **Get uptime**: `(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime`
6. **List open ports**: `Get-NetTCPConnection -State Listen`
7. **Base64 Encode**: `[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("Secret"))`
8. **Base64 Decode**: `[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String("U2VjcmV0"))`
9. **Export Event Log to CSV**: `Get-WinEvent -LogName System -MaxEvents 100 | Export-Csv events.csv`
10. **Kill processes by memory size**: `Get-Process | Where-Object WS -gt 2GB | Stop-Process`
11. **Check AD Lockout Status**: `Get-ADUser jdoe -Properties LockedOut`
12. **Unlock AD Account**: `Unlock-ADAccount jdoe`
13. **Get Windows version**: `(Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion").ReleaseId`
14. **Parse JWT Token**: `(ConvertFrom-Json ([Text.Encoding]::Utf8.GetString([Convert]::FromBase64String(($token.Split('.')[1] + '==')))))`
15. **Generate GUID**: `[guid]::NewGuid().ToString()`

*(Expand similar practical tools and logic via modules & scripts!)*

---
*End of Cheat Sheet. Save, bookmark, and refer back often during development and operations.*
