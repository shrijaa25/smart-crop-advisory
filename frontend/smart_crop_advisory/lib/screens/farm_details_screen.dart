import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../services/auth_controller.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';

class FarmDetailsScreen extends StatefulWidget {
  final AuthController auth;

  const FarmDetailsScreen({super.key, required this.auth});

  @override
  State<FarmDetailsScreen> createState() => _FarmDetailsScreenState();
}

class _FarmDetailsScreenState extends State<FarmDetailsScreen> {
  final _formKey = GlobalKey<FormState>();
  final _controllers = <String, TextEditingController>{
    for (final key in [
      'name',
      'village',
      'district',
      'state',
      'area',
      'soil',
      'irrigation',
      'latitude',
      'longitude',
    ])
      key: TextEditingController(),
  };
  String _areaUnit = 'acre';
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    double? number(String key) {
      final text = _controllers[key]!.text.trim();
      return text.isEmpty ? null : double.parse(text);
    }

    try {
      await widget.auth.createFarm({
        'name': _controllers['name']!.text.trim(),
        'village': _optional('village'),
        'district': _optional('district'),
        'state': _optional('state'),
        'area_value': number('area'),
        'area_unit': _areaUnit,
        'soil_type': _optional('soil'),
        'irrigation_method': _optional('irrigation'),
        'latitude': number('latitude'),
        'longitude': number('longitude'),
      });
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = error is ApiException
              ? error.message
              : 'Could not save farm details. Try again.',
        );
      }
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  String? _optional(String key) {
    final text = _controllers[key]!.text.trim();
    return text.isEmpty ? null : text;
  }

  String? _numberValidator(
    String? value, {
    double? min,
    double? max,
    bool required = false,
  }) {
    if (value == null || value.trim().isEmpty) {
      return required ? 'Required.' : null;
    }
    final parsed = double.tryParse(value.trim());
    if (parsed == null) {
      return 'Enter a number.';
    }
    if (min != null && parsed < min) {
      return 'Must be at least $min.';
    }
    if (max != null && parsed > max) {
      return 'Must be at most $max.';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Farm details')),
    body: SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 700),
          child: Form(
            key: _formKey,
            child: ListView(
              padding: const EdgeInsets.all(AppSpace.xl),
              children: [
                Text('Add a farm', style: AppText.h2),
                const SizedBox(height: AppSpace.sm),
                Text(
                  'This farm will be linked to your signed-in account.',
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
                const SizedBox(height: AppSpace.lg),
                _field('Farm name', 'name', required: true),
                _field('Village', 'village'),
                _field('District', 'district'),
                _field('State', 'state'),
                Row(
                  children: [
                    Expanded(
                      child: _field(
                        'Farm area (optional)',
                        'area',
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                        ),
                        validator: (v) => _numberValidator(v, min: 0.001),
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
                          DropdownMenuItem(value: 'acre', child: Text('Acre')),
                          DropdownMenuItem(
                            value: 'hectare',
                            child: Text('Hectare'),
                          ),
                        ],
                        onChanged: _busy
                            ? null
                            : (v) => setState(() => _areaUnit = v ?? 'acre'),
                      ),
                    ),
                  ],
                ),
                _field('Soil type', 'soil'),
                _field('Irrigation method', 'irrigation'),
                Row(
                  children: [
                    Expanded(
                      child: _field(
                        'Latitude (optional)',
                        'latitude',
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                          signed: true,
                        ),
                        validator: (v) =>
                            _numberValidator(v, min: -90, max: 90),
                      ),
                    ),
                    const SizedBox(width: AppSpace.md),
                    Expanded(
                      child: _field(
                        'Longitude (optional)',
                        'longitude',
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                          signed: true,
                        ),
                        validator: (v) =>
                            _numberValidator(v, min: -180, max: 180),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpace.md),
                FilledButton(
                  onPressed: _busy ? null : _save,
                  child: _busy
                      ? const CircularProgressIndicator()
                      : const Text('Save farm'),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );

  Widget _field(
    String label,
    String key, {
    bool required = false,
    TextInputType? keyboardType,
    String? Function(String?)? validator,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpace.md),
    child: TextFormField(
      controller: _controllers[key],
      keyboardType: keyboardType,
      decoration: InputDecoration(labelText: label),
      validator:
          validator ??
          (required
              ? (v) =>
                    v == null || v.trim().isEmpty ? 'Enter a farm name.' : null
              : null),
    ),
  );
}
