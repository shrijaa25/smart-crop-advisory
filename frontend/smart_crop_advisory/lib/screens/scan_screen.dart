import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../theme/app_colors.dart';
import '../services/auth_controller.dart';
import '../services/api_client.dart';

class ScanScreen extends StatefulWidget {
  final AuthController auth;
  const ScanScreen({super.key, required this.auth});
  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  final _picker = ImagePicker();
  XFile? _image;
  bool _busy = false;
  String? _message;
  Map<String, dynamic>? _prediction;

  Future<void> _pick(ImageSource source) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      final selected = await _picker.pickImage(
        source: source,
        maxWidth: 2200,
        maxHeight: 2200,
        imageQuality: 88,
      );
      if (!mounted) return;
      if (selected != null) {
        setState(() {
          _image = selected;
          _prediction = null;
          _message = 'Photo selected. Tap Analyze Photo to get a prediction.';
        });
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => _message =
              'Could not access the image. Check camera or photo permissions in your device settings and try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _analyze() async {
    final image = _image;
    if (_busy || image == null) return;

    setState(() {
      _busy = true;
      _message = null;
      _prediction = null;
    });
    try {
      final result = await widget.auth.predictDisease(image);
      if (mounted) setState(() => _prediction = result);
    } on ApiException catch (error) {
      if (mounted) setState(() => _message = error.message);
    } catch (_) {
      if (mounted) {
        setState(
          () => _message =
              'Could not reach the prediction service. Check that the backend is running and the API address is correct.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(20),
    children: [
      Text('Scan Your Crop', style: Theme.of(context).textTheme.headlineMedium),
      const SizedBox(height: 6),
      const Text('Capture a clear picture of your plant to inspect it.'),
      const SizedBox(height: 20),
      Container(
        height: 300,
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          color: AppColors.primaryLight,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.border),
        ),
        child: _image == null
            ? const Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.eco_outlined, size: 58, color: AppColors.primary),
                  SizedBox(height: 12),
                  Text('Your crop photo will appear here'),
                ],
              )
            : Stack(
                fit: StackFit.expand,
                children: [
                  Image(
                    image: kIsWeb
                        ? NetworkImage(_image!.path)
                        : FileImage(File(_image!.path)) as ImageProvider,
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) => const Center(
                      child: Text(
                        'Image preview is unavailable on this device.',
                      ),
                    ),
                  ),
                  Positioned(
                    right: 10,
                    top: 10,
                    child: IconButton.filledTonal(
                      tooltip: 'Remove image',
                      onPressed: () => setState(() {
                        _image = null;
                        _message = null;
                        _prediction = null;
                      }),
                      icon: const Icon(Icons.close),
                    ),
                  ),
                ],
              ),
      ),
      const SizedBox(height: 16),
      FilledButton.icon(
        onPressed: _busy ? null : () => _pick(ImageSource.camera),
        icon: const Icon(Icons.photo_camera_outlined),
        label: const Text('Take Photo'),
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
      ),
      const SizedBox(height: 10),
      OutlinedButton.icon(
        onPressed: _busy ? null : () => _pick(ImageSource.gallery),
        icon: const Icon(Icons.photo_library_outlined),
        label: const Text('Choose from Gallery'),
        style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(50)),
      ),
      const SizedBox(height: 10),
      FilledButton.icon(
        onPressed: _busy || _image == null ? null : _analyze,
        icon: const Icon(Icons.biotech_outlined),
        label: const Text('Analyze Photo'),
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
      ),
      if (_busy)
        const Padding(
          padding: EdgeInsets.all(18),
          child: Column(
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 10),
              Text('Analyzing the leaf photo…'),
            ],
          ),
        ),
      if (_prediction != null) ...[
        const SizedBox(height: 16),
        _PredictionCard(result: _prediction!),
      ],
      if (_message != null) ...[
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Text(_message!),
          ),
        ),
      ],
      const Padding(
        padding: EdgeInsets.all(8),
        child: Text(
          'A photo or automated prediction cannot confirm disease or trigger pesticide treatment.',
        ),
      ),
    ],
  );
}

class _PredictionCard extends StatelessWidget {
  final Map<String, dynamic> result;

  const _PredictionCard({required this.result});

  @override
  Widget build(BuildContext context) {
    final disease = result['disease'] as String? ?? 'Unknown';
    final marathi = result['disease_marathi'] as String? ?? '';
    final confidence = (result['confidence'] as num?)?.toDouble() ?? 0;
    final isConfident = result['is_confident'] == true;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.eco, color: AppColors.primary),
                const SizedBox(width: 8),
                Text(
                  'Prediction result',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            const SizedBox(height: 14),
            Text(disease, style: Theme.of(context).textTheme.headlineSmall),
            if (marathi.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(marathi, style: Theme.of(context).textTheme.titleMedium),
            ],
            const SizedBox(height: 12),
            Text('Confidence: ${(confidence * 100).toStringAsFixed(1)}%'),
            const SizedBox(height: 8),
            Text(
              isConfident
                  ? 'Use this result as a guide and inspect the plant for symptoms.'
                  : 'The model is unsure. Take a closer, clearer leaf photo and try again.',
            ),
          ],
        ),
      ),
    );
  }
}
