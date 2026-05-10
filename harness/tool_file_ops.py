"""
文件操作工具模块
基于 Rust 实现的 file_ops.rs 翻译而来
"""

import os
import io
from dataclasses import dataclass, asdict
from typing import Optional, Tuple, List, Any

# 最大读取文件大小（10 MB）
MAX_READ_SIZE: int = 10 * 1024 * 1024

# 最大写入文件大小（10 MB）
MAX_WRITE_SIZE: int = 10 * 1024 * 1024


@dataclass
class TextFilePayload:
    """文本文件读取结果的负载结构"""
    file_path: str
    content: str
    num_lines: int
    start_line: int
    total_lines: int


@dataclass
class ReadFileOutput:
    """read_file 方法的输出结构"""
    kind: str
    file: TextFilePayload

    def to_dict(self):
        """转换为 JSON 可序列化的字典"""
        result = asdict(self)
        return result


@dataclass
class StructuredPatchHunk:
    """结构化补丁块"""
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    lines: List[str]


@dataclass
class WriteFileOutput:
    """write_file 方法的输出结构"""
    kind: str
    file_path: str
    content: str
    structured_patch: List[StructuredPatchHunk]
    original_file: Optional[str]
    git_diff: Optional[Any]

    def to_dict(self):
        """转换为 JSON 可序列化的字典"""
        result = asdict(self)
        if self.structured_patch:
            result['structured_patch'] = [asdict(hunk) for hunk in self.structured_patch]
        return result


@dataclass
class EditFileOutput:
    """edit_file 方法的输出结构"""
    file_path: str
    old_string: str
    new_string: str
    original_file: str
    structured_patch: List[StructuredPatchHunk]
    user_modified: bool
    replace_all: bool
    git_diff: Optional[Any]

    def to_dict(self):
        """转换为 JSON 可序列化的字典"""
        result = asdict(self)
        if self.structured_patch:
            result['structured_patch'] = [asdict(hunk) for hunk in self.structured_patch]
        return result


def is_binary_file(path: str) -> bool:
    """
    检查文件是否为二进制文件
    通过检查文件开头的缓冲区是否包含 NUL 字节来判断
    """
    try:
        with open(path, 'rb') as f:
            buffer = f.read(8192)
            return b'\x00' in buffer
    except IOError:
        return False


def normalize_path(path: str) -> str:
    """
    规范化路径：将相对路径转换为绝对路径，并解析符号链接
    """
    if os.path.isabs(path):
        candidate = path
    else:
        candidate = os.path.join(os.getcwd(), path)
    
    # 解析符号链接
    try:
        return os.path.realpath(candidate)
    except OSError:
        raise FileNotFoundError(f"Cannot resolve path: {path}")


def normalize_path_allow_missing(path: str) -> str:
    """
    规范化路径（允许文件不存在）：将相对路径转换为绝对路径，
    如果文件不存在则规范化父目录路径
    """
    if os.path.isabs(path):
        candidate = path
    else:
        candidate = os.path.join(os.getcwd(), path)
    
    # 尝试解析符号链接
    try:
        return os.path.realpath(candidate)
    except OSError:
        # 文件不存在，尝试规范化父目录
        parent = os.path.dirname(candidate)
        if parent:
            try:
                canonical_parent = os.path.realpath(parent)
            except OSError:
                canonical_parent = parent
            filename = os.path.basename(candidate)
            return os.path.join(canonical_parent, filename)
        return candidate


def make_patch(original: str, updated: str) -> List[StructuredPatchHunk]:
    """
    生成结构化补丁
    基于原始内容和更新后内容生成类似 diff 的补丁信息
    """
    lines: List[str] = []
    
    # 添加删除的行（前缀 -）
    for line in original.splitlines():
        lines.append(f"-{line}")
    
    # 添加新增的行（前缀 +）
    for line in updated.splitlines():
        lines.append(f"+{line}")
    
    return [StructuredPatchHunk(
        old_start=1,
        old_lines=len(original.splitlines()),
        new_start=1,
        new_lines=len(updated.splitlines()),
        lines=lines
    )]


def read_file(
    path: str,
    offset: Optional[int] = None,
    limit: Optional[int] = None
) -> ReadFileOutput:
    """
    读取文本文件并返回行窗口化的结果
    
    Args:
        path: 文件路径（支持相对路径和绝对路径）
        offset: 起始行偏移量（从 0 开始）
        limit: 读取的最大行数
    
    Returns:
        ReadFileOutput: 包含文件内容和元数据的结果对象
    
    Raises:
        FileNotFoundError: 文件不存在
        PermissionError: 权限不足
        ValueError: 文件过大或为二进制文件
    """
    # 规范化路径
    absolute_path = normalize_path(path)
    
    # 检查文件大小
    file_size = os.path.getsize(absolute_path)
    if file_size > MAX_READ_SIZE:
        raise ValueError(
            f"File is too large ({file_size} bytes, max {MAX_READ_SIZE} bytes)"
        )
    
    # 检测二进制文件
    if is_binary_file(absolute_path):
        raise ValueError("File appears to be binary")
    
    # 读取文件内容
    with open(absolute_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按行分割
    lines = content.splitlines()
    start_index = offset if offset is not None else 0
    start_index = min(start_index, len(lines))
    
    # 计算结束索引
    if limit is not None:
        end_index = start_index + limit
    else:
        end_index = len(lines)
    end_index = min(end_index, len(lines))
    
    # 提取选定范围的内容
    selected = '\n'.join(lines[start_index:end_index])
    
    return ReadFileOutput(
        kind="text",
        file=TextFilePayload(
            file_path=absolute_path,
            content=selected,
            num_lines=end_index - start_index,
            start_line=start_index + 1,  # 转换为 1-based
            total_lines=len(lines)
        )
    ).to_dict()


def write_file(path: str, content: str) -> WriteFileOutput:
    """
    替换文件内容并返回补丁元数据
    
    Args:
        path: 文件路径（支持相对路径和绝对路径）
        content: 要写入的新内容
    
    Returns:
        WriteFileOutput: 包含写入结果和补丁信息的对象
    
    Raises:
        PermissionError: 权限不足
        ValueError: 内容过大
    """
    # 验证内容大小
    if len(content) > MAX_WRITE_SIZE:
        raise ValueError(
            f"Content is too large ({len(content)} bytes, max {MAX_WRITE_SIZE} bytes)"
        )
    
    # 规范化路径（允许文件不存在）
    absolute_path = normalize_path_allow_missing(path)
    
    # 读取原始文件内容（如果文件存在）
    original_file: Optional[str] = None
    if os.path.exists(absolute_path):
        with open(absolute_path, 'r', encoding='utf-8') as f:
            original_file = f.read()
    
    # 确保父目录存在
    parent_dir = os.path.dirname(absolute_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)
    
    # 写入新内容
    with open(absolute_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 生成补丁信息
    structured_patch = make_patch(original_file or "", content)
    
    return WriteFileOutput(
        kind="update" if original_file is not None else "create",
        file_path=absolute_path,
        content=content,
        structured_patch=structured_patch,
        original_file=original_file,
        git_diff=None
    ).to_dict()


def edit_file(
    path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False
) -> EditFileOutput:
    """
    在文件中执行字符串替换并返回补丁元数据
    
    Args:
        path: 文件路径（支持相对路径和绝对路径）
        old_string: 要被替换的旧字符串
        new_string: 替换后的新字符串
        replace_all: 是否替换所有匹配项（默认只替换第一个）
    
    Returns:
        EditFileOutput: 包含替换结果和补丁信息的对象
    
    Raises:
        FileNotFoundError: 文件不存在
        PermissionError: 权限不足
        ValueError: 新旧字符串相同或旧字符串未找到
    """
    # 规范化路径
    absolute_path = normalize_path(path)
    
    # 读取原始文件内容
    with open(absolute_path, 'r', encoding='utf-8') as f:
        original_file = f.read()
    
    # 验证：新旧字符串必须不同
    if old_string == new_string:
        raise ValueError("old_string and new_string must differ")
    
    # 验证：旧字符串必须存在于文件中
    if old_string not in original_file:
        raise ValueError("old_string not found in file")
    
    # 执行替换
    if replace_all:
        updated = original_file.replace(old_string, new_string)
    else:
        updated = original_file.replace(old_string, new_string, 1)
    
    # 验证写入内容大小
    if len(updated) > MAX_WRITE_SIZE:
        raise ValueError(
            f"Content is too large ({len(updated)} bytes, max {MAX_WRITE_SIZE} bytes)"
        )
    
    # 写入更新后的内容
    with open(absolute_path, 'w', encoding='utf-8') as f:
        f.write(updated)
    
    # 生成补丁信息
    structured_patch = make_patch(original_file, updated)
    
    return EditFileOutput(
        file_path=absolute_path,
        old_string=old_string,
        new_string=new_string,
        original_file=original_file,
        structured_patch=structured_patch,
        user_modified=False,
        replace_all=replace_all,
        git_diff=None
    ).to_dict()


if __name__ == "__main__":
    # 示例用法
    import tempfile
    import os
    
    # 创建临时测试文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Hello World!\nThis is a test file.\nHello again!")
        test_path = f.name
    # test_path = os.path.abspath("/Users/Ray/FufanAi/harness/mini_harness/demo_outputs/progress.md")
    try:
        # 测试 read_file
        print("=== Testing read_file ===")
        result = read_file(test_path, offset=1, limit=3)
        print(f"Read content: {result.file.content!r}")
        print(f"Start line: {result.file.start_line}, Total lines: {result.file.total_lines}")
        
        # 测试 write_file（更新现有文件）
        print("\n=== Testing write_file (update) ===")
        write_result = write_file(test_path, "New content\nwith multiple\nlines")
        print(f"Write kind: {write_result.kind}")
        print(f"File path: {write_result.file_path}")
        print(f"Original file exists: {write_result.original_file is not None}")
        
        # 验证写入结果
        with open(test_path, 'r') as f:
            print(f"File content after write:\n{f.read()}")
        
        # 测试 write_file（创建新文件）
        print("\n=== Testing write_file (create) ===")
        new_file_path = os.path.join(os.path.dirname(test_path), "new_file.txt")
        create_result = write_file(new_file_path, "This is a brand new file!")
        print(f"Write kind: {create_result.kind}")
        print(f"File path: {create_result.file_path}")
        print(f"Original file exists: {create_result.original_file is not None}")
        
        # 验证新文件创建
        with open(new_file_path, 'r') as f:
            print(f"New file content:\n{f.read()}")
        
        # 测试 edit_file
        print("\n=== Testing edit_file ===")
        edit_result = edit_file(test_path, "New", "Updated", replace_all=False)
        print(f"Edited {edit_result.file_path}")
        print(f"Replaced '{edit_result.old_string}' with '{edit_result.new_string}'")
        print(f"Replace all: {edit_result.replace_all}")
        
        # 验证修改结果
        with open(test_path, 'r') as f:
            print(f"File content after edit:\n{f.read()}")
            
    finally:
        # pass
        # 清理临时文件
        os.unlink(test_path)
        if 'new_file_path' in locals():
            os.unlink(new_file_path)
