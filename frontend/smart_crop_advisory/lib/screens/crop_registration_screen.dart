import 'package:flutter/material.dart';

import '../models/farm.dart';
import '../services/api_client.dart';
import '../services/auth_controller.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';
import 'farm_details_screen.dart';

class CropRegistrationScreen extends StatefulWidget {
  final AuthController auth;

  const CropRegistrationScreen({super.key, required this.auth});

  @override
  State<CropRegistrationScreen> createState() => _CropRegistrationScreenState();
}

class _CropRegistrationScreenState extends State<CropRegistrationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _variety = TextEditingController();
  final _area = TextEditingController();
  late Future<List<Farm>> _farms;
  int? _farmId;
  String _crop = 'tomato';
  String _areaUnit = 'acre';
  DateTime? _plantingDate;
  bool _busy = false;
  String? _error;
  bool _dateMissing = false;

  @override
  void initState() {
    super.initState();
    _farms = widget.auth.loadFarms();
  }

  @override
  void dispose() {
    _variety.dispose();
    _area.dispose();
    super.dispose();
  }

  Future<void> _refreshFarms() async {
    setState(() => _farms = widget.auth.loadFarms());
    final rows = await _farms;
    if (rows.isNotEmpty && mounted) {
      setState(() => _farmId ??= rows.first.id);
    }
  }

  Future<void> _addFarm() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => FarmDetailsScreen(auth: widget.auth)),
    );
    if (saved == true && mounted) {
      await _refreshFarms();
    }
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final date = await showDatePicker(
      context: context,
      initialDate: _plantingDate ?? now,
      firstDate: DateTime(1950),
      lastDate: DateTime(now.year, now.month, now.day),
      helpText: 'Select transplanting date',
    );
    if (date != null) {
      setState(() {
        _plantingDate = date;
        _dateMissing = false;
      });
    }
  }

  Future<void> _save() async {
    if (_busy) return;
    final fieldsValid = _formKey.currentState!.validate();
    if (_farmId == null || _plantingDate == null) {
      setState(() {
        _dateMissing = _plantingDate == null;
        _error = _farmId == null ? 'Choose one of your farms.' : null;
      });
      return;
    }
    if (!fieldsValid) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.auth.createCropCycle(_farmId!, {
        'crop_name': _crop,
        'variety': _variety.text.trim().isEmpty ? null : _variety.text.trim(),
        'planting_date': _dateString(_plantingDate!),
        'planting_method': 'transplanting',
        'area_value': double.parse(_area.text.trim()),
        'area_unit': _areaUnit,
      });
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      // A timed-out POST may have committed. Check the authenticated list before
      // presenting a retry that could create a duplicate crop cycle.
      try {
        final cycles = await widget.auth.loadCropCycles();
        final date = _plantingDate!;
        final area = double.parse(_area.text.trim());
        final variety = _variety.text.trim();
        final wasCreated = cycles.any(
          (cycle) =>
              cycle.farmId == _farmId &&
              cycle.cropName == _crop &&
              cycle.variety == (variety.isEmpty ? null : variety) &&
              cycle.plantingDate.year == date.year &&
              cycle.plantingDate.month == date.month &&
              cycle.plantingDate.day == date.day &&
              cycle.areaValue == area &&
              cycle.areaUnit == _areaUnit,
        );
        if (wasCreated && mounted) {
          Navigator.of(context).pop(true);
          return;
        }
      } catch (_) {
        // Keep the original save error; failed confirmation is not success.
      }
      if (mounted) {
        setState(
          () => _error = error is ApiException
              ? error.message
              : 'Could not register this crop. Try again.',
        );
      }
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  String _dateString(DateTime value) =>
      '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Register crop')),
    body: SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 680),
          child: FutureBuilder<List<Farm>>(
            future: _farms,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return Center(
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpace.xl),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          snapshot.error is ApiException
                              ? (snapshot.error as ApiException).message
                              : 'Could not load your farms.',
                          textAlign: TextAlign.center,
                        ),
                        TextButton.icon(
                          onPressed: _busy ? null : _refreshFarms,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                );
              }
              final farms = snapshot.data ?? const <Farm>[];
              if (_farmId == null && farms.isNotEmpty) {
                _farmId = farms.first.id;
              }
              return ListView(
                padding: const EdgeInsets.all(AppSpace.xl),
                children: [
                  Text('Let’s set up your farm', style: AppText.h2),
                  const SizedBox(height: AppSpace.sm),
                  Text(
                    'Crop age is counted from the transplanting date.',
                    style: AppText.bodyMuted,
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: AppSpace.md),
                    Semantics(
                      liveRegion: true,
                      child: Text(
                        _error!,
                        style: AppText.small.copyWith(color: Colors.red),
                      ),
                    ),
                  ],
                  if (farms.isEmpty) ...[
                    const SizedBox(height: AppSpace.xl),
                    const Text('Add a farm before registering a crop.'),
                    const SizedBox(height: AppSpace.md),
                    OutlinedButton.icon(
                      onPressed: _addFarm,
                      icon: const Icon(Icons.add),
                      label: const Text('Add farm'),
                    ),
                  ] else ...[
                    const SizedBox(height: AppSpace.xl),
                    Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          DropdownButtonFormField<int>(
                            initialValue:
                                farms.any((farm) => farm.id == _farmId)
                                ? _farmId
                                : farms.first.id,
                            decoration: const InputDecoration(
                              labelText: 'Farm',
                            ),
                            items: farms
                                .map(
                                  (farm) => DropdownMenuItem(
                                    value: farm.id,
                                    child: Text(farm.name),
                                  ),
                                )
                                .toList(),
                            onChanged: _busy
                                ? null
                                : (value) => setState(() => _farmId = value),
                          ),
                          const SizedBox(height: AppSpace.md),
                          DropdownButtonFormField<String>(
                            initialValue: _crop,
                            decoration: const InputDecoration(
                              labelText: 'Crop',
                            ),
                            items: const [
                              DropdownMenuItem(
                                value: 'tomato',
                                child: Text('Tomato'),
                              ),
                              DropdownMenuItem(
                                value: 'chilli',
                                child: Text('Chilli'),
                              ),
                            ],
                            onChanged: _busy
                                ? null
                                : (value) =>
                                      setState(() => _crop = value ?? 'tomato'),
                          ),
                          const SizedBox(height: AppSpace.md),
                          TextFormField(
                            controller: _variety,
                            decoration: const InputDecoration(
                              labelText: 'Crop variety (optional)',
                              hintText: 'Enter the variety you are growing',
                            ),
                            textCapitalization: TextCapitalization.words,
                          ),
                          const SizedBox(height: AppSpace.md),
                          OutlinedButton.icon(
                            onPressed: _busy ? null : _pickDate,
                            icon: const Icon(Icons.calendar_month_outlined),
                            label: Text(
                              _plantingDate == null
                                  ? 'Transplanting date'
                                  : 'Transplanting date: ${_dateString(_plantingDate!)}',
                            ),
                          ),
                          if (_dateMissing) ...[
                            const SizedBox(height: AppSpace.xs),
                            Text(
                              'Select a transplanting date.',
                              style: AppText.small.copyWith(color: Colors.red),
                            ),
                          ],
                          const SizedBox(height: AppSpace.md),
                          Row(
                            children: [
                              Expanded(
                                child: TextFormField(
                                  controller: _area,
                                  keyboardType:
                                      const TextInputType.numberWithOptions(
                                        decimal: true,
                                      ),
                                  decoration: const InputDecoration(
                                    labelText: 'Farm area',
                                  ),
                                  validator: (value) {
                                    final parsed = double.tryParse(
                                      value?.trim() ?? '',
                                    );
                                    return parsed == null ||
                                            !parsed.isFinite ||
                                            parsed <= 0
                                        ? 'Enter an area above zero.'
                                        : null;
                                  },
                                ),
                              ),
                              const SizedBox(width: AppSpace.md),
                              Expanded(
                                child: DropdownButtonFormField<String>(
                                  initialValue: _areaUnit,
                                  decoration: const InputDecoration(
                                    labelText: 'Area unit',
                                  ),
                                  items: const [
                                    DropdownMenuItem(
                                      value: 'acre',
                                      child: Text('Acre'),
                                    ),
                                    DropdownMenuItem(
                                      value: 'hectare',
                                      child: Text('Hectare'),
                                    ),
                                  ],
                                  onChanged: _busy
                                      ? null
                                      : (value) => setState(
                                          () => _areaUnit = value ?? 'acre',
                                        ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: AppSpace.xl),
                          FilledButton(
                            onPressed: _busy ? null : _save,
                            child: _busy
                                ? const CircularProgressIndicator()
                                : const Text('Save Crop & Continue'),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              );
            },
          ),
        ),
      ),
    ),
  );
}
