from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from apps.accounts.models.verification_codes import EmailVerificationCode
from django.template.loader import render_to_string
from email.mime.image import MIMEImage
import os

def send_verification_email_to_user(user):
    """
    Create verification code and send email to user
    """
    # Mark previous codes as used
    EmailVerificationCode.objects.filter(
        user=user,
        is_used=False
    ).update(is_used=True)

    # Create new verification code
    verification = EmailVerificationCode.objects.create(user=user)

    # Prepare email content
    subject = 'Verify Your Email Address'

    # Email context
    context = {
        'user': user,
        'verification_code': verification.verification_code,
        'expires_at': verification.expires_at,
    }

    html_message = render_to_string('emails/verification_email.html', context)
    plain_message = render_to_string('emails/verification_email.txt', context)

    email = EmailMultiAlternatives(
        subject=subject,
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )

    email.attach_alternative(html_message, "text/html")

    image_path = 'staticfiles/logos/dermazeen-logo.png'

    with open(image_path, 'rb') as img_file:
        img = MIMEImage(img_file.read())
        img.add_header('Content-ID', '<logo_cid>')
        img.add_header('Content-Disposition', 'inline', filename=os.path.basename(image_path))
        email.attach(img)
    email.send(fail_silently=False)

    return verification
