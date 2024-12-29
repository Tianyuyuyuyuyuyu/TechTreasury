import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:path/path.dart' as path;
import 'package:package_info_plus/package_info_plus.dart';
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class UpdateService {
  static const String UPDATE_CHECK_URL = 'http://120.26.201.54/api/check-update.php';
  static const String LAST_UPDATE_CHECK_KEY = 'last_update_check';

  /// 检查更新
  static Future<UpdateInfo?> checkForUpdate() async {
    try {
      // 获取当前应用版本信息
      final packageInfo = await PackageInfo.fromPlatform();
      final currentVersion = packageInfo.version;

      // 获取最后检查更新的时间
      final prefs = await SharedPreferences.getInstance();
      final lastCheck = prefs.getInt(LAST_UPDATE_CHECK_KEY) ?? 0;
      final now = DateTime.now().millisecondsSinceEpoch;

      // 如果距离上次检查不足24小时，则跳过
      if (now - lastCheck < const Duration(hours: 24).inMilliseconds) {
        return null;
      }

      // 更新最后检查时间
      await prefs.setInt(LAST_UPDATE_CHECK_KEY, now);

      // 检查服务器最新版本
      final response = await http.get(Uri.parse(UPDATE_CHECK_URL));
      if (response.statusCode != 200) {
        throw Exception('Failed to check for updates');
      }

      final updateInfo = UpdateInfo.fromJson(json.decode(response.body));

      // 比较版本号
      if (_shouldUpdate(currentVersion, updateInfo.version)) {
        return updateInfo;
      }

      return null;
    } catch (e) {
      print('Error checking for updates: $e');
      return null;
    }
  }

  /// 下载更新
  static Future<String?> downloadUpdate(String url) async {
    try {
      final response = await http.get(Uri.parse(url));
      if (response.statusCode != 200) {
        throw Exception('Failed to download update');
      }

      // 保存到临时目录
      final tempDir = await Directory.systemTemp.createTemp('app_update');
      final file = File(path.join(tempDir.path, 'update.exe'));
      await file.writeAsBytes(response.bodyBytes);

      return file.path;
    } catch (e) {
      print('Error downloading update: $e');
      return null;
    }
  }

  /// 安装更新
  static Future<bool> installUpdate(String filePath) async {
    try {
      // 在Windows上执行安装程序
      final process = await Process.start(
        filePath,
        ['/SILENT'], // 静默安装参数
        mode: ProcessStartMode.detached,
      );

      // 退出当前应用
      exit(0);

      return true;
    } catch (e) {
      print('Error installing update: $e');
      return false;
    }
  }

  /// 比较版本号
  static bool _shouldUpdate(String currentVersion, String newVersion) {
    final current = currentVersion.split('.').map(int.parse).toList();
    final latest = newVersion.split('.').map(int.parse).toList();

    for (var i = 0; i < 3; i++) {
      if (latest[i] > current[i]) return true;
      if (latest[i] < current[i]) return false;
    }

    return false;
  }
}

/// 更新信息模型
class UpdateInfo {
  final String version;
  final String downloadUrl;
  final String releaseNotes;

  UpdateInfo({
    required this.version,
    required this.downloadUrl,
    required this.releaseNotes,
  });

  factory UpdateInfo.fromJson(Map<String, dynamic> json) {
    return UpdateInfo(
      version: json['version'],
      downloadUrl: json['downloadUrl'],
      releaseNotes: json['releaseNotes'],
    );
  }
}
