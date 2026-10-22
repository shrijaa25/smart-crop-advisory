import 'package:flutter/material.dart';

import '../models/crop_cycle.dart';
import '../models/farm.dart';
import '../services/api_client.dart';
import '../services/auth_controller.dart';
import '../theme/app_colors.dart';

class ProfileScreen extends StatefulWidget {
  final AuthController auth;
  const ProfileScreen({super.key, required this.auth});
  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late Future<_ProfileData> _future;
  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_ProfileData> _load() async {
    final rows = await Future.wait([
      widget.auth.loadFarms(),
      widget.auth.loadCropCycles(),
    ]);
    return _ProfileData(rows[0] as List<Farm>, rows[1] as List<CropCycle>);
  }

  void _refresh() => setState(() => _future = _load());

  Future<void> _logout() async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Log out?'),
        content: const Text(
          'You’ll need to sign in again to access your farm information.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Log out'),
          ),
        ],
      ),
    );
    if (yes != true || !mounted) return;
    try {
      await widget.auth.logout();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              error is ApiException
                  ? error.message
                  : 'Could not finish logging out. Try again.',
            ),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final profile = widget.auth.profile;
    final fullName = profile?.fullName.trim() ?? '';
    final initials = fullName.isEmpty
        ? '?'
        : fullName
              .split(RegExp(r'\s+'))
              .take(2)
              .map((p) => p[0].toUpperCase())
              .join();
    return FutureBuilder<_ProfileData>(
      future: _future,
      builder: (context, snap) => RefreshIndicator(
        onRefresh: () async => _refresh(),
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text('Profile', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 18),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 30,
                      backgroundColor: AppColors.primaryLight,
                      child: Text(
                        initials,
                        style: const TextStyle(
                          color: AppColors.primary,
                          fontSize: 20,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            fullName.isEmpty ? 'Name unavailable' : fullName,
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          if (profile?.phone case final phone?) Text(phone),
                          if (profile?.preferredLanguage case final lang?)
                            Text('Language: ${_language(lang)}'),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            if (snap.connectionState == ConnectionState.waiting &&
                !snap.hasData)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (snap.hasError && !snap.hasData)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Farm summary is unavailable.'),
                      Text(
                        snap.error is ApiException
                            ? (snap.error as ApiException).message
                            : 'Check your connection.',
                      ),
                      TextButton(
                        onPressed: _refresh,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
              )
            else if (snap.data case final data?) ...[
              Text(
                'Farm & crops',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Card(
                child: Column(
                  children: [
                    ListTile(
                      leading: const Icon(Icons.agriculture_outlined),
                      title: const Text('Farms'),
                      trailing: Text('${data.farms.length}'),
                    ),
                    const Divider(height: 1),
                    ListTile(
                      leading: const Icon(Icons.eco_outlined),
                      title: const Text('Crop cycles'),
                      trailing: Text('${data.cycles.length}'),
                    ),
                    for (final cycle in data.cycles)
                      ListTile(
                        dense: true,
                        title: Text(_cropName(cycle)),
                        subtitle: Text(cycle.status),
                        trailing: cycle.areaValue == null
                            ? null
                            : Text('${cycle.areaValue} ${cycle.areaUnit}'),
                      ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 24),
            OutlinedButton.icon(
              onPressed: _logout,
              icon: const Icon(Icons.logout),
              label: const Text('Log out'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.danger,
                minimumSize: const Size.fromHeight(50),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProfileData {
  final List<Farm> farms;
  final List<CropCycle> cycles;
  const _ProfileData(this.farms, this.cycles);
}

String _language(String code) => switch (code.toLowerCase()) {
  'en' => 'English',
  'hi' => 'Hindi',
  'te' => 'Telugu',
  'ta' => 'Tamil',
  'kn' => 'Kannada',
  'mr' => 'Marathi',
  _ => code,
};
String _cropName(CropCycle cycle) =>
    '${cycle.cropName[0].toUpperCase()}${cycle.cropName.substring(1)}${cycle.variety == null ? '' : ' · ${cycle.variety}'}';
