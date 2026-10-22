import 'package:flutter/material.dart';

import '../models/crop_cycle.dart';
import '../models/farm.dart';
import '../services/api_client.dart';
import '../services/auth_controller.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';
import 'crop_registration_screen.dart';
import 'farm_details_screen.dart';

class MyCropsScreen extends StatefulWidget {
  final AuthController auth;

  const MyCropsScreen({super.key, required this.auth});

  @override
  State<MyCropsScreen> createState() => _MyCropsScreenState();
}

class _MyCropsScreenState extends State<MyCropsScreen> {
  late Future<(List<Farm>, List<CropCycle>)> _data;
  final Map<int, Future<Map<String, dynamic>>> _stageLookups = {};

  @override
  void initState() {
    super.initState();
    _data = _load();
  }

  Future<(List<Farm>, List<CropCycle>)> _load() async {
    final results = await Future.wait([
      widget.auth.loadFarms(),
      widget.auth.loadCropCycles(),
    ]);
    return (results[0] as List<Farm>, results[1] as List<CropCycle>);
  }

  void _refresh() => setState(() {
    _stageLookups.clear();
    _data = _load();
  });

  Future<void> _openFarmForm() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => FarmDetailsScreen(auth: widget.auth)),
    );
    if (saved == true && mounted) _refresh();
  }

  Future<void> _openCropForm() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => CropRegistrationScreen(auth: widget.auth),
      ),
    );
    if (saved == true && mounted) _refresh();
  }

  Future<Map<String, dynamic>> _stage(CropCycle crop) =>
      _stageLookups.putIfAbsent(
        crop.id,
        () => widget.auth.loadCropStage(crop.id, DateTime.now()),
      );

  @override
  Widget build(BuildContext context) => RefreshIndicator(
    onRefresh: () async => _refresh(),
    child: FutureBuilder<(List<Farm>, List<CropCycle>)>(
      future: _data,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          final error = snapshot.error;
          return ListView(
            padding: const EdgeInsets.all(AppSpace.xxl),
            children: [
              Text('Crop dashboard', style: AppText.h1),
              const SizedBox(height: AppSpace.xl),
              _notice(
                error is ApiException
                    ? error.message
                    : 'Could not load farms and crops.',
                error: true,
              ),
              TextButton.icon(
                onPressed: _refresh,
                icon: const Icon(Icons.refresh),
                label: const Text('Try again'),
              ),
            ],
          );
        }
        final (farms, cycles) = snapshot.data ?? (<Farm>[], <CropCycle>[]);
        return ListView(
          padding: const EdgeInsets.all(AppSpace.xxl),
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Farm and crop dashboard', style: AppText.h1),
                      const SizedBox(height: AppSpace.xs),
                      Text(
                        '${farms.length} farms · ${cycles.length} crop cycles',
                        style: AppText.bodyMuted,
                      ),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'Refresh',
                  onPressed: _refresh,
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            const SizedBox(height: AppSpace.lg),
            Wrap(
              spacing: AppSpace.md,
              runSpacing: AppSpace.md,
              children: [
                FilledButton.icon(
                  onPressed: _openFarmForm,
                  icon: const Icon(Icons.add_home_outlined),
                  label: const Text('Add farm'),
                ),
                OutlinedButton.icon(
                  onPressed: _openCropForm,
                  icon: const Icon(Icons.add),
                  label: const Text('Register crop'),
                ),
              ],
            ),
            const SizedBox(height: AppSpace.xl),
            if (farms.isEmpty)
              _notice(
                'No farms are registered yet. Add your farm to get started.',
              )
            else
              ...farms.map(
                (farm) => _farmCard(
                  farm,
                  cycles.where((crop) => crop.farmId == farm.id).toList(),
                ),
              ),
          ],
        );
      },
    ),
  );

  Widget _farmCard(Farm farm, List<CropCycle> crops) => Container(
    margin: const EdgeInsets.only(bottom: AppSpace.lg),
    padding: const EdgeInsets.all(AppSpace.lg),
    decoration: BoxDecoration(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppSpace.radiusCard),
      border: Border.all(color: AppColors.border),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(farm.name, style: AppText.h3),
        const SizedBox(height: AppSpace.xs),
        Text(
          [farm.village, farm.district, farm.state]
              .whereType<String>()
              .where((v) => v.isNotEmpty)
              .join(', ')
              .ifEmpty('Location not provided'),
          style: AppText.bodyMuted,
        ),
        const SizedBox(height: AppSpace.xs),
        Text(
          [
            if (farm.areaValue != null)
              'Area ${farm.areaValue} ${farm.areaUnit}',
            if (farm.soilType?.isNotEmpty == true) 'Soil ${farm.soilType}',
            if (farm.irrigationMethod?.isNotEmpty == true)
              'Irrigation ${farm.irrigationMethod}',
          ].join(' · ').ifEmpty('Farm details recorded'),
          style: AppText.small,
        ),
        const SizedBox(height: AppSpace.lg),
        if (crops.isEmpty)
          Text(
            'No crops registered on this farm yet.',
            style: AppText.bodyMuted,
          )
        else
          ...crops.map(_cropCard),
      ],
    ),
  );

  Widget _cropCard(CropCycle crop) => Container(
    width: double.infinity,
    margin: const EdgeInsets.only(bottom: AppSpace.md),
    padding: const EdgeInsets.all(AppSpace.md),
    decoration: BoxDecoration(
      color: AppColors.bg,
      borderRadius: BorderRadius.circular(AppSpace.radiusInput),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${_cropLabel(crop.cropName)}${crop.variety?.isNotEmpty == true ? ' · ${crop.variety}' : ''}',
          style: AppText.label,
        ),
        const SizedBox(height: AppSpace.xs),
        Text(
          'Transplanted ${_dateString(crop.plantingDate)} · ${crop.areaValue ?? 'Area not set'} ${crop.areaUnit}',
          style: AppText.small,
        ),
        const SizedBox(height: AppSpace.xs),
        FutureBuilder<Map<String, dynamic>>(
          future: _stage(crop),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return Text(
                'Checking crop age and verified stage…',
                style: AppText.small,
              );
            }
            if (snapshot.hasError) {
              return Text('Crop stage unavailable.', style: AppText.small);
            }
            final stage = snapshot.data ?? const <String, dynamic>{};
            final age = stage['crop_age_days'] as int?;
            final stageName = stage['stage_name'] as String?;
            if (age != null && age < 0) {
              return Text(
                'Not transplanted yet (age counted from transplanting).',
                style: AppText.small,
              );
            }
            return Text(
              [
                if (age != null) 'Crop age: $age days',
                if (stageName != null)
                  'Verified stage: $stageName'
                else
                  'Stage unavailable: no unique verified stage rule matches',
              ].join(' · '),
              style: AppText.small,
            );
          },
        ),
      ],
    ),
  );

  String _cropLabel(String crop) => crop == 'chilli' ? 'Chilli' : 'Tomato';
  String _dateString(DateTime value) =>
      '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

  Widget _notice(String text, {bool error = false}) => Container(
    padding: const EdgeInsets.all(AppSpace.lg),
    decoration: BoxDecoration(
      color: (error ? AppColors.danger : AppColors.primary).withValues(
        alpha: 0.08,
      ),
      borderRadius: BorderRadius.circular(AppSpace.radiusCard),
    ),
    child: Text(
      text,
      style: AppText.body.copyWith(
        color: error ? AppColors.danger : AppColors.textPrimary,
      ),
    ),
  );
}

extension on String {
  String ifEmpty(String replacement) => isEmpty ? replacement : this;
}
