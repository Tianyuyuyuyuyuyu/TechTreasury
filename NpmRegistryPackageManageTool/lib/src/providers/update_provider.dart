import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/update_service.dart';

final updateProvider = Provider<UpdateNotifier>((ref) {
  return UpdateNotifier();
});

class UpdateNotifier {
  Future<UpdateInfo?> checkForUpdates() async {
    return await UpdateService.checkForUpdate();
  }

  Future<String?> downloadUpdate(String url) async {
    return await UpdateService.downloadUpdate(url);
  }

  Future<bool> installUpdate(String filePath) async {
    return await UpdateService.installUpdate(filePath);
  }
}
